import json
import os
import pandas as pd
import pprint
import re
import requests
import settings
import socket
import sys
from bs4 import BeautifulSoup
from dropbox import settings as dropbox_settings
from tqdm import *


def parse_response(possible_dict, keys_of_interest, single_person_dict={}):
    try:
        this_dict_keys = possible_dict.keys()
        for key in keys_of_interest:
            if key in this_dict_keys:
                if (key == 'name') and ('visible_in_newtube' in this_dict_keys):
                    single_person_dict['discipline'] = possible_dict[key]
                elif key != 'name':
                    check_for_nicknames(possible_dict, key)

    except AttributeError:
        return AttributeError

    return single_person_dict


# I did this because so many conditional statements in one function made me feel gross.
# TODO: do this better
def check_for_nicknames(possible_dict, key):
    this_dict_keys = possible_dict.keys()
    if key != 'first_name':
        single_person_dict[key] = possible_dict[key]
    else:
        if ('nickname' in this_dict_keys) and (possible_dict['nickname']):
            single_person_dict[key] = possible_dict['nickname']
        else:
            single_person_dict[key] = possible_dict[key]


if __name__ == '__main__':
    keys_of_interest = ['email_address',
                        'first_name',
                        'last_name',
                        'name',
                        'hired_at']

    sys.setrecursionlimit(3000)

    # target_url = 'https://inside.ideo.com/users/search?user_location_ids%5B%5D=3'
    base_url = 'https://inside.ideo.com/users/search?_=1519678038902&page={}&replace=false&sort=relevance&sort_dir=desc&sort_direction_name=desc&user_location_ids%5B%5D=3'

    target_urls = [base_url.format(1), base_url.format(2)]

    people_urls = []

    for target_url in target_urls:
        response = requests.get(target_url,
                                headers=dropbox_settings.HEADERS,
                                timeout=5,
                                )

        soup = BeautifulSoup(response.text, "lxml")

        people_info = soup.find_all('a', {'class': ['\\"js-headshot-wrapper\\"']})

        for div in people_info:
            people_urls.append(div['href'].strip())

    combined_list = []
    project_lists = {}
    for url in people_urls:
        url.replace('\\', '').strip()
        user = url.split('/')[-1].split('\\')[0]
        target_url = 'https://inside.ideo.com/users/' + user
        print('this is the target url', target_url)

        response = requests.get(target_url,
                                headers=dropbox_settings.HEADERS,
                                timeout=5,
                                )
        # turn content into a dictionary

        person_info = json.loads(response.content)

        # extract info that we want
        single_person_dict = {}

        for info_dict in person_info:
            parser_response = parse_response(info_dict, keys_of_interest, single_person_dict)
            if parser_response == AttributeError:
                for info_list in info_dict:
                    parse_response(info_list, keys_of_interest, single_person_dict)

        # sys.exit()

        project_page_url = 'https://inside.ideo.com/users/{}/get_my_work_projects'.format(user)

        response = requests.get(project_page_url,
                                headers=dropbox_settings.HEADERS,
                                timeout=5,
                                )

        try:
            project_jsons = response.json()['projects']['Core team']
            project_id_list = []
            project_name_list = []
            projects = {}
            for p_json in project_jsons:
                project_id_list.append(p_json['id'])
                project_name_list.append(p_json['name'])
                projects[p_json['id']] = p_json['name']
            project_lists[single_person_dict['email_address']] = project_id_list

        except KeyError:
            project_lists[single_person_dict['email_address']] = []

        combined_list.append(single_person_dict)

    with open(settings.inside_ideo_json, 'w') as fp:
        json.dump(project_lists, fp)
    print('saved file ', settings.inside_ideo_json)

    people_info_df = pd.DataFrame(combined_list)
    people_info_df.to_csv(settings.inside_ideo_csv, index=False)
