# Stdlib imports
import urllib3
import json
from datetime import datetime

# Third-party app imports
import requests
import certifi
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from elasticsearch import Elasticsearch, helpers
from newspaper import Article
from pymongo import MongoClient

# Imports from app
from middleware.config import (
    ELASTICSEARCH_USER,
    ELASTICSEARCH_PASSWORD,
    CONTEXT_API_USERNAME,
    CONTEXT_API_PASSWORD,
)

# Removing requests warning
urllib3.disable_warnings()
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# MongoDB setup
client = MongoClient(connect=False)
db = client.elastic_sync
articles_collection = db.articles

# Context Setup
base_url = 'https://context.newsai.org/api'

# Elasticsearch setup
es = Elasticsearch(
    ['https://search.newsai.org'],
    http_auth=(ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORD),
    port=443,
    use_ssl=True,
    verify_certs=True,
    ca_certs=certifi.where(),
)


def get_login_token():
    headers = {
        "content-type": "application/json",
        "accept": "application/json"
    }
    payload = {
        "username": CONTEXT_API_USERNAME,
        "password": CONTEXT_API_PASSWORD,
    }

    r = requests.post(base_url + "/jwt-token/",
                      headers=headers, data=json.dumps(payload), verify=False)
    data = json.loads(r.text)
    token = data.get('token')
    return token


def check_if_article_in_es(url):
    articles = es.search(index='articles', q='url:"' + url + '"')
    if articles['hits']['total'] is 1:
        return True
    return False


def sync_articles_es(articles):
    if articles:
        to_append = []
        has_completed_article = False
        for article in articles:
            doc = None
            if not check_if_article_in_es(article['url']):
                if articles_collection.find_one({'url': article['url']}) is None:
                    article_data = Article(article['url'])
                    article_data.download()
                    article_data.parse()
                    doc = {
                        '_type': 'article',
                        '_index': 'articles',
                        'title': article_data.title,
                        'text': article_data.text,
                        'url': article['url']
                    }
                    articles_collection.insert_one(doc)
                else:
                    doc = articles_collection.find_one({'url': article['url']})
                    doc['_index'] = 'articles'
                if '_id' in doc:
                    del doc['_id']
                print doc
                to_append.append(doc)
            else:
                has_completed_article = True
        res = helpers.bulk(es, to_append)
        return (res, has_completed_article)


def get_articles():
    token = get_login_token()
    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "authorization": "Bearer " + token
    }

    r = requests.get(base_url + '/articles/',
                     headers=headers, verify=False)
    articles = r.json()
    offset = 100
    for x in range(0, articles['count'], offset):
        print x
        r = requests.get(base_url + '/articles/?limit=' + str(offset) + '&offset=' + str(x) + '&fields=url',
                         headers=headers, verify=False)
        article = r.json()
        res, has_completed_article = sync_articles_es(article['results'])
        if has_completed_article:
            return True
    return True


def process_single_article(url):
    articles = [{
        'url': url
    }]
    res, has_completed_article = sync_articles_es(articles)
    return (res, has_completed_article)


def deploy_new_update():
    get_articles()


def reset_elastic():
    es.indices.delete(index='articles', ignore=[400, 404])
    es.indices.create(index='articles', ignore=[400, 404])

# reset_elastic()
deploy_new_update()
