# Elastic lr4

## Usage

### 1. Run server

```
sudo docker compose up --build
```

### 2. Run client

```
sudo docker build -t lr4-client .
```

## Tasks

1. Create new index (if doesn't exists)

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client create
```

2. Index book 

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client add-fb2 -a "Tolstoy" --name "Voina i peace" wm.fb2
```

3. Get part by pointer

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client get-text 1-1-V
```

with word limit 

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client get-text --limit 50 1-1-V
```

4. Get chapter's pointer by phrase

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client get-chapter "как домашний человек"
```
 
5. Get summary

- by chapter:

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client summarize-text --chapter 1-1-VII 
```

- by phrase:

```
sudo docker run --rm --network "elastic-lr4_elastic" lr4-client summarize-text -t "как домашний человек"
```
