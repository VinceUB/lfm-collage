#!/usr/bin/env python3

import requests
import configparser
import json
from PIL import Image
from PIL import ImageChops
import os.path
import os
from statistics import fmean

def get_config():
    config = configparser.ConfigParser()
    config.read('lfm.ini')

    username = config['Options']['Username']
    api_key = config['Options']['ApiKey']
    
    outputs = {}
    for section, values in config.items():
        if not section.startswith('Output'):
            continue
        name = section.split('-', 1)[-1]
        outputs[name] = {}
        outputs[name]['grid'] = map(int, values.get('Grid', '10x10').split('x'))
        size = values.get('OutputSize', None)
        outputs[name]['size'] = map(int, size.split('x')) if size else None
        outputs[name]['quality'] = int(values.get('Quality', 60))
        outputs[name]['path'] = values.get('SavePath', 'collage.jpg')


    return {'username': username, 'api_key': api_key, 'outputs': outputs}


def get_albums(username, api_key, limit=16*9, period='12month'):
    return requests.get(
            'http://ws.audioscrobbler.com/2.0/',
            params={
                'method': 'user.gettopalbums',
                'user': username,
                'api_key': api_key,
                'format': 'json',
                'limit': limit,
                'period': period
            }
        ).json()['topalbums']['album']

def fetch_image(album) -> Image.Image:
    image_url = album['image'][-1]['#text']
    
    if not image_url:
        return None
    
    try:
        filename = f'./covers/{image_url.split("/")[-1]}'
        if not os.path.isdir('./covers'):
            os.mkdir('./covers')
        if not os.path.isfile(filename):
            imagecontent = requests.get(image_url).content
            with open(filename, 'wb') as f:
                f.write(imagecontent)
        return Image.open(filename).convert('RGB')
    except:
        print(f'\tError at: {album["name"]}')
        return None


def image_alpha(image):
    total = 0
    colourlist = image.getcolors(100000)
    for colour in colourlist:
        grey = 0
        grey = sum(colour[1])/3
        total += colour[0]*grey
    return total / (image.size[0]*image.size[1])

def image_hue(image):
    total = 0
    colourlist = image.convert('HSV').getcolors(100000)
    for colour in colourlist:
        hue = 0
        hue = colour[1][0]
        total += colour[0]*hue
    return total / (image.size[0]*image.size[1])

def remove_lfm_dups(albums):
    def normn(a):
        return a['name']\
                .replace('-','(')\
                .replace(':','(')\
                .replace('&','and')\
                .replace("'",'')\
                .split('(')[0]\
                .strip()\
                .lower()
    seen = set()
    seen_add = seen.add
    return [a for a in albums if not (normn(a) in seen or seen_add(normn(a)))]


def shuffle_images(images, sort_fn=image_alpha):
    return sorted(
            images, 
            key=lambda i: sort_fn(i),
            reverse=True
            )

def make_collage(images, grid=(16, 9), cell=(300, 300)):
    collage = Image.new('RGB', (cell[0]*grid[0], cell[1]*grid[1]))
    
    x = 0
    y = 0
    i = 0
    for y in range(grid[1]):
        for x in range(grid[0]):
            collage.paste(images[i], (x*cell[0], y*cell[1], (x+1)*cell[0], (y+1)*cell[1]))
            i+=1
    return collage

def collage_pipeline(username, api_key, grid=(32,18), output_size=None, image_dims=(300,300)) -> Image:
    albums = get_albums(username, api_key,
                        limit=int(grid[0]*grid[1]*1.2))
    albums = remove_lfm_dups(albums)
    images = [fetch_image(a) for a in albums]
    images = list(filter(None, images))
    images = shuffle_images(images[:grid[0]*grid[1]])
    output_size = output_size or (grid[0]*image_dims[0], grid[1]*image_dims[1])
    return make_collage(images, grid=grid).resize(output_size, Image.LANCZOS)

four_k = (3820,2160)
teneightyp = (1920,1080)
teneightyp_mob = (1080,1920)

config = get_config()
for _, output in config['outputs'].items():
    collage_pipeline(
            config['username'],
            config['api_key'],
            grid=tuple(output['grid']),
            output_size=tuple(output['size'])
            ).save(output['path'], optimize=True, quality=output['quality'])
