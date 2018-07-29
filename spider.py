#!/usr/bin/env python
# -*- coding' : 'UTF-8 -*-',

import requests
from urllib.parse import urlencode
from pyquery import PyQuery as pq
import pymongo
from settings import *
import re

client = pymongo.MongoClient(MONGODB_URL)
db = client[MONGODB_DB]


base_url = 'http://weixin.sogou.com/weixin?'

headers = {
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding' : 'gzip, deflate',
    'Accept-Language' : 'zh-CN,zh;q=0.9',
    'Cache-Control' : 'max-age=0',
    'Connection' : 'keep-alive',
    'Cookie' : 'SUV=00C32540DF4A423B5ACB1F3ABAAFF891; CXID=A54081B5DAF67A9C87C983B22B13DF03; SUID=36424ADF3565860A5AD18F94000D55B4; SMYUV=1531179968584141; IPLOC=CN4401; SNUID=364149DC020771183F9B7C8E03CAF38D; ld=Flllllllll2bgFONlllllVHNnq1lllllT1Ij2yllll9lllll4ylll5@@@@@@@@@@; LSTMV=417%2C147; LCLKINT=2372; ABTEST=8|1532666715|v1; weixinIndexVisited=1; sct=2; JSESSIONID=aaawmpiuo7uiI9cgUFHsw; ppinf=5|1532836289|1534045889|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZTozNjolRTUlOEYlQUElRTglOEIlQTUlRTUlODglOUQlRTglQTclODF8Y3J0OjEwOjE1MzI4MzYyODl8cmVmbmljazozNjolRTUlOEYlQUElRTglOEIlQTUlRTUlODglOUQlRTglQTclODF8dXNlcmlkOjQ0Om85dDJsdUxINzhQamVOWkowZnBCRlRZT25kZzRAd2VpeGluLnNvaHUuY29tfA; pprdig=KxTZyXOmLprq_I4Kzyx89NdYnDmvrA4k0kUuWmhGNP_CJcVo_ZOQlUNWMOi4MwVe00b2d3nszrr6tKUaxldaTKHL3ofBXtM6_Dysl1g6KneiHb4HuADlol--PFtZf1VhEtFXYXhlpwfEgZm51LvJqwyEKbD6Mk6tQhzW4-al5Ec; sgid=12-36322365-AVtdOcHrF82HB9sg5rerU5U; ppmdig=1532836290000000b3de27869ace6a5519293f1294539576',
    'Host' : 'weixin.sogou.com',
    'Upgrade-Insecure-Requests' : '1',
    'User-Agent' : 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
}

# 本地代理池API
proxy_url = 'http://127.0.0.1:5000/get'

proxy = None
max_count = 5
def get_proxy():
    try:
        response = requests.get(proxy_url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def get_html(url, count=1):
    print('Crawling: ', url)
    print('Tring Count: ', count)
    global proxy
    if count >= max_count:
        print('Tried Too Many Counts')
        return None
    try:
        if proxy:
            # 如果有代理
            proxies = {
                'http' : 'http://' + proxy
            }
            response = requests.get(url, allow_redirects=False, headers=headers, proxies=proxies)
        else:
            response = requests.get(url, allow_redirects=False, headers=headers)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            print('Requests 302 ERROR')
            proxy = get_proxy()
            if proxy:
                print('Using Proxy', proxy)
                return get_html(url)
            else:
                print('Get Proxy Failed')
                return None

    except ConnectionError as e:
        print('Error Occurred', e.args)
        proxy = get_proxy()
        count += 1
        return get_html(url, count)

def get_index(keyword, page):
    data = {
        'query' : keyword,
        'type' : 2,
        'page' : page,
    }
    queries = urlencode(data)
    url = base_url + queries
    html = get_html(url)
    return html

def parse_html(html):
    doc = pq(html)
    items = doc('.news-box .news-list .txt-box h3 a').items()
    for item in items:
        yield item.attr('href')

def get_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
    except ConnectionError:
        return None

def parse_detail(html):
    doc = pq(html)
    title = doc('.rich_media_title').text().strip()
    content = doc('.rich_media_content').text()
    # date = doc('#publish_time').text()
    # 由于页面加载后使用了ajax加载了部分数据，使用正则匹配日期
    date = re.search('var\spublish_time.*?"(.*?)".*?;', html).group(1)
    nickname = doc('.profile_container .profile_inner .profile_nickname').text()
    wechat = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
    return {
        'title' : title,
        'content' : content,
        'date' : date,
        'nickname' : nickname,
        'wechat' : wechat,
    }

def save_to_mongo(data):
    if db['articles'].update({'title' : data['title']}, {'$set' : data}, True):
        print('Saved to Mongo', data['title'])
    else:
        print('Saved to Mongo Failed', data['title'])

def main():
    for page in range(1, 101):
        html = get_index(KEYWORD, page)
        if html:
            article_urls = parse_html(html)
            for article_url in article_urls:
                article_html = get_detail(article_url)
                if article_html:
                    article_data = parse_detail(article_html)
                    print(article_data)
                    save_to_mongo(article_data)

if __name__ == '__main__':
    main()