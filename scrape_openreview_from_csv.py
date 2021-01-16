import time
import os
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from bs4 import BeautifulSoup
from selenium import webdriver
from tqdm import tqdm


# Author object
class Author:
    def __init__(self, name, affil):
        self.name = name
        self.affil = affil
        self.num_total = 0
        self.num_accept = 0
        self.num_reject = 0
        self.scores = []
        self.scores_accept = []
        self.first_author = 0
        self.last_author = 0

    def update(self, authors_list, score, is_accepted):
        self.num_total += 1
        self.scores.append(score)

        if is_accepted:
            self.num_accept += 1
            self.scores_accept.append(score)
        else:
            self.num_reject += 1

        if self.name == authors_list[0]:
            self.first_author += 1
        elif self.name == authors_list[-1]:
            # elif to only increment solo author's first authorship, not senior
            self.last_author += 1


# Affiliation (organization) object
class Affiliation:
    def __init__(self, name):
        self.name = name
        self.num_total = 0
        self.num_accept = 0
        self.num_reject = 0
        self.scores = []
        self.scores_accept = []

    def update(self, score, is_accepted):
        self.num_total += 1
        self.scores.append(score)

        if is_accepted:
            self.num_accept += 1
            self.scores_accept.append(score)
        else:
            self.num_reject += 1

if __name__ == "__main__":
    # If haven't downloaded csvs, do so
    author_csv_path = 'authors_iclr2021.csv'
    affil_csv_path = 'affiliations_iclr2021.csv'

    if not os.path.exists(author_csv_path) or not os.path.exists(affil_csv_path):
        # Start selenium
        options = webdriver.FirefoxOptions()
        options.headless = True
        driver = webdriver.Firefox(options=options)
        
        # Downloaded csv at https://docs.google.com/spreadsheets/d/1n58O0lgGI5kI0QQY9f4BDDpNB4oFjb5D51yMr9fHAK4/edit#gid=1546418007
        csv_path = 'iclr2021_results_final.csv'
        df = pd.read_csv(csv_path)
        
        # Init dict records
        authors_dict = {}
        affils_dict = defaultdict(int)

        # Go through each paper
        for _, paper in tqdm(df.iterrows(), total=df.shape[0]):
            # Paper info
            url, score, is_accepted = paper['url'], paper['avg_rating'], 'Accept' in paper['final_decision']
            
            # Nav to paper on openreview
            driver.get(url)
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Authors info
            author_hrefs = [x['href'] for x in soup.find_all("a", {'data-placement': 'top'})]
            author_names = [x.text for x in soup.find_all("a", {'data-placement': 'top'})]
            base_url = 'https://openreview.net'

            # Go through each author in paper
            this_paper_affils = []
            for author_href, author_name in zip(author_hrefs, author_names):
                author_url = base_url + author_href
                driver.get(author_url)
                author_html = driver.page_source
                author_soup = BeautifulSoup(author_html, 'html.parser')
                
                author_id = author_href.replace('/profile?id=', '')

                try:
                    author_affil = author_soup.find('div', class_='title-container').h3.contents[0]
                except:
                    author_affil = None
               
                # Record author
                if author_id not in authors_dict:
                    authors_dict[author_id] = Author(author_name, author_affil)
                authors_dict[author_id].update(author_names, score, is_accepted)
                
                # Record affiliation, once per paper
                if author_affil not in this_paper_affils and author_affil is not None:
                    if author_affil not in affils_dict:
                        affils_dict[author_affil] = Affiliation(author_affil)
                    else:
                        affils_dict[author_affil].update(score, is_accepted)
        
        author_out_rows = [[a.name, 
                            a.affil, 
                            a.num_total, 
                            a.num_accept, 
                            a.num_reject, 
                            (sum(a.scores) / float(len(a.scores))) if len(a.scores) > 0 else 0,
                            (sum(a.scores_accept) / float(len(a.scores_accept))) if len(a.scores_accept) > 0 else 0,
                            a.first_author,
                            a.last_author
                            ] for a in authors_dict.values()]
        author_df = pd.DataFrame(author_out_rows, columns=['Name',
                                                           'Affiliation',
                                                           'Submitted',
                                                           'Accepted',
                                                           'Rejected',
                                                           'AvgScore',
                                                           'AvgAcceptedScore',
                                                           'FirstAuthorCount',
                                                           'LastAuthorCount'
                                                           ])
        print(author_df)
        author_accepted_df = author_df.sort_values('Accepted', ascending=False)
        author_first_author_df = author_df.sort_values('FirstAuthorCount', ascending=False)
        author_last_author_df = author_df.sort_values('LastAuthorCount', ascending=False)
        
        author_accepted_df.to_csv('authors_iclr2021.csv', index=False)
        author_first_author_df.to_csv('authors_first_iclr2021.csv', index=False)
        author_last_author_df.to_csv('authors_last_iclr2021.csv', index=False)
        print(f'Saved to author info to csvs')
        
        affil_out_rows = [[a.name, 
                           a.num_total, 
                           a.num_accept, 
                           a.num_reject, 
                           (sum(a.scores) / float(len(a.scores))) if len(a.scores) > 0 else 0,
                           (sum(a.scores_accept) / float(len(a.scores_accept))) if len(a.scores_accept) > 0 else 0,
                           ] for a in affils_dict.values()]
        affil_df = pd.DataFrame(affil_out_rows, columns=['Name',
                                                         'Submitted',
                                                         'Accepted',
                                                         'Rejected',
                                                         'AvgScore',
                                                         'AvgAcceptedScore',
                                                         ])
        print(affil_df)
        affil_accepted_df = affil_df.sort_values('Accepted', ascending=False)
        affil_avgacceptedscore_df = affil_df.sort_values('AvgAcceptedScore', ascending=False)
        affil_avgscore_df = affil_df.sort_values('AvgScore', ascending=False)
        
        affil_accepted_df.to_csv('affiliations_iclr2021.csv', index=False)
        affil_avgacceptedscore_df.to_csv('affiliations_avgacceptedscore_iclr2021.csv', index=False)
        affil_avgscore_df.to_csv('affiliations_avgscore_iclr2021.csv', index=False)

        print(f'Saved to affil info to csvs')

    else:
        # Open saved author info
        author_df = pd.read_csv(author_csv_path)
        
        print(author_df)
        
        author_accepted_df = author_df.sort_values('Accepted', ascending=False)
        author_first_author_df = author_df.sort_values('FirstAuthorCount', ascending=False)
        author_last_author_df = author_df.sort_values('LastAuthorCount', ascending=False)
        
        # Open saved affiliation info
        affil_df = pd.read_csv(affil_csv_path)
        
        affil_accepted_df = affil_df.sort_values('Accepted', ascending=False)
        affil_avgacceptedscore_df = affil_df.sort_values('AvgAcceptedScore', ascending=False)
        affil_avgscore_df = affil_df.sort_values('AvgScore', ascending=False)
        
        print(affil_df)
    
    print('Open the ipython notebook for visualizing data in pretty graphs')
