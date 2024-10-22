from sys import exit, argv
from elasticsearch import Elasticsearch
from loguru import logger
from lxml import etree
import spacy
from spacy.lang.ru.stop_words import STOP_WORDS
from string import punctuation
from collections import Counter


def connect() -> Elasticsearch:
    passwd = open("../.env").readline().split('=')[-1]
    es = Elasticsearch('http://elasticsearch:9200', basic_auth=("elastic", passwd))
    settings = {
        "settings": {
            "analysis": {
                "filter": {
                    "russian_stop": {
                        "type": "stop",
                        "stopwords": "_russian_"
                    }
                },
                "analyzer": {
                    "custom_russian": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "russian_stop",
                            "snowball",
                        ]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "custom_russian"
                },
                "author": {
                    "type": "text",
                    "analyzer": "custom_russian"
                },
                "content": {
                    "type": "text",
                    "analyzer": "custom_russian"
                },
                "volume": {"type": "integer"},
                "section": {"type": "integer"},
                "chapter": {"type": "text"},
            }
        }
    }
    
    if es.ping():
        # es.delete_by_query(index='2020-3-07-kos', body={"query": {"match_all": {}}})
        # es.options(ignore_status=[400,404]).indices.delete(index='2020-3-07-kos')
        logger.success('Connected! Checking index...')
        if es.indices.exists(index="2020-3-07-kos"):
            logger.success("Index already exist!")            
        else:
            es.indices.create(index="2020-3-07-kos", body=settings)
            logger.success("Index created!")
        return es
    else:
        logger.error('Can\'t connect to ElasticSearch')
        return None


def index_book(author: str, name: str, val: str) -> None:
    section_names = {"первая": 1, "вторая": 2, "третья": 3,}
    es = connect()
    if es is None:
        logger.error(f'Can\'t establish connection to ElasticSearch')
        exit(100)
    try:
        logger.info('Reading file...')
        parser = etree.XMLParser(recover=True)
        tree = etree.parse("../data/" + val, parser)
    except Exception as e:
        logger.error(f"File open error: {e}")
        exit(101)
    try:
        logger.info('Parsing file...')
        root = tree.getroot()
        ns = {'fb': 'http://www.gribuser.ru/xml/fictionbook/2.0'}
        sections = []
        chapters = []
        contnets_common = []
        contents = []
        body = root.findall(".//fb:body", namespaces=ns)[0]
        for sec in body.findall(".//fb:section", namespaces=ns):
            for title in sec.findall(".//fb:title", namespaces=ns):
                for p in title.findall(".//fb:p", namespaces=ns):
                    if "Часть" in p.text: 
                        sections.append(section_names[p.text[p.text.find("Часть")+6::]])
                    else:
                        chapters.append(p.text)
            for sec_p in sec.findall(".//fb:p", namespaces=ns):
                contnets_common.append(sec_p.text)
        for i in range(len(chapters)-1):
            new_chap = contnets_common[contnets_common.index(chapters[i]): contnets_common.index(chapters[i+1])]
            contents.append('\n'.join(new_chap).replace('\\t', '    ').replace('\\n', '\n'))
        contents = list(set(contents))
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        exit(102)
    try:
        logger.info('Indexing documents...')
        for content in contents:
            if len(content) != 0:
                doc = {
                    "volume": 1,
                    "section": sections[0],
                    "chapter": content[:content.find('\n')],
                    "title": author,
                    "author": name,
                    "content": content
                }
                es.index(index="2020-3-07-kos", document=doc)
        logger.success("Successfully indexed book")
    except Exception as e:
        logger.error(f"Index document error: {e}")
        exit(103)


def show(val: str, limit=0, mute=False) -> str:
    es = connect()
    if es is None:
        logger.error(f'Can\'t establish connection to ElasticSearch')
        exit(100)
    volume, section, chapter = val.split('-')
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"volume": int(volume)}},
                    {"term": {"section": int(section)}},
                    {"match": {"chapter": chapter}}
                ]
            }
        }
    }
     
    hits = es.search(index="2020-3-07-kos", body=query)
    res = hits['hits']['hits'][0]['_source']['content'] \
        if limit == 0 else hits['hits']['hits'][0]['_source']['content'][:int(limit)]
    if not mute:
        print(res)
    return res


def search(val: str, mute=False) -> list:
    es = connect()
    if es is None:
        logger.error(f'Can\'t establish connection to ElasticSearch')
        exit(100)
    query = {
        'query': {
            'match_phrase': {
                'content': val
            }
        }
    }
     
    hits = es.search(index="2020-3-07-kos", body=query)
    res = []
    for hit in hits['hits']['hits']:
        res.append(str(hit['_source']['volume']) + '-' +
                   str(hit['_source']['section']) + '-' +
                   hit['_source']['chapter'])
    if not mute:
        for i in res:
            print(i)
    return res


def refer(text='', chapter = ''):
    if text == chapter == '' or (text != '' and chapter != ''):
        logger.error('Only one parameter must be specified')
        exit(110)
    try:
        if chapter:
            chapter_text = show(chapter, mute=True)  
        else:
            chapter_text = search(text, mute=True)
            if len(chapter_text) > 0:
                chapter_text = show(chapter_text[0], mute=True)
            else:
                logger.error('No matching')
                exit(111)
        nlp = spacy.load("./tools/ru_core_news_lg/ru_core_news_lg/ru_core_news_lg-3.7.0")
        doc = nlp(chapter_text)
        keywords = []
        tags = ['PROPN', 'ADJ', 'NOUN', 'VERB']
        
        for token in doc:
            if(token.text in nlp.Defaults.stop_words or token.text in punctuation):
                continue
            if(token.pos_ in tags):
                keywords.append(token.text)

        word_freq = Counter(keywords)
        max_freq = Counter(keywords).most_common(1)[0][1]
        for w in word_freq:
            word_freq[w] = (word_freq[w]/max_freq)
        sent_power={}
        for sent in doc.sents:
            for word in sent:
                if word.text in word_freq.keys():
                    if sent in sent_power.keys():
                        sent_power[sent]+=word_freq[word.text]
                    else:
                        sent_power[sent]=word_freq[word.text]
        summary = []

        sorted_x = sorted(sent_power.items(), key=lambda kv: kv[1], reverse=True)
        
        counter = 0
        for i in range(len(sorted_x)):
            summary.append(str(sorted_x[i][0]).capitalize())
            counter += 1
            if(counter >= 10):
                break
        print('=='*20 + 'REFFER' + '=='*20)
        print(' '.join(summary))
        print(f"{len(' '.join(summary))}/{len(chapter_text)}")

    except Exception as e:
        logger.error(f"Error referring chapter: {e}")
        exit(115)



if __name__ == "__main__":
    # index_book("Tolstoy", "Voyna i peace", "wm.fb2")
    # show("1-1-V", 50)
    # search("самые разнородные")
    # refer(text="садилась в темноте кареты")
    FUNCTION_MAP = {'create' : (connect, None),
                    'add-fb2' : (index_book, ('author', 'name', 'val')),
                    'get-text': (show, ('val', 'limit')),
                    'get-chapter': (search, ('val')),
                    'summarize-text': (refer, ('text', 'chapter'))
                    }
    params = {'author': '', 'name': '', 'limit': 0, 'text': '', 'chapter': '', 'val': ''}
    flags = [('-a', '--author'), ('-n', '--name'), ('-l', '--limit'), ('-t', '--text'), ('-c', '--chapter')]

    line = argv[:-1] if '-' not in argv[-2] else argv    
    params['val'] = argv[-1] if (argv[-2][0] != '-' and argv[1] != 'create') else ''

    logger.info(line)
    for pos in range(len(line)):
        for pair in flags:
            if line[pos] in pair:
                params[pair[1][2:]] = line[pos+1]
    command = FUNCTION_MAP[argv[1]][0]
    arguments_list = FUNCTION_MAP[argv[1]][1]
    arguments = dict()
    for key in params.keys():
        if params[key]:
            arguments[key] = params[key]
    try:
        logger.info(params)
        logger.info(arguments)
        command(**arguments)
    except Exception as e:
        logger.error(f"Incorrect usage: {e}")
        exit(120)
