#!/usr/bin/env python
# coding: utf-8

# In[1]:


import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


# In[ ]:


import pandas as pd
from collections import Counter


# In[ ]:


movies = pd.read_csv("data/ml-latest/movies.csv")
ratings = pd.read_csv("data/ml-latest/ratings.csv")


# In[68]:


movieidx = movies.merge(ratings[['movieId', 'rating']].groupby('movieId').aggregate('mean'), on='movieId').set_index('movieId')
titletomovie = movies[['movieId', 'title']].set_index('title').to_dict()['movieId']
genres = movies[['movieId', 'genres']].set_index('movieId').to_dict()['genres']


# In[3]:


movies.columns, ratings.columns


# In[4]:


moviesByUser = ratings.groupby("userId")["movieId"].apply(list)


# In[6]:


from gensim.models import Word2Vec

model = Word2Vec(window = 10, sg = 1, hs = 0,
                 negative = 10, # for negative sampling
                 alpha=0.03, min_alpha=0.0007, min_count=50,
                 seed = 14, workers=20)
model.build_vocab(moviesByUser, progress_per=200)
model.train(moviesByUser, total_examples = model.corpus_count, 
            epochs=10, report_delay=1)
print(model)


# In[78]:


model.save("movielens.model")


# In[49]:


def similar_products(v, n = 6):
    # extract most similar products for the input vector
    ms = model.wv.most_similar(v, topn= n+1)[1:]
    
    # extract name and similarity score of the similar products
    new_ms = []
    for j in ms:
        # pair = (products_dict[j[0]][0], j[1])
        new_ms.append(j[0])
        
    return new_ms 

def bought_along(product):
    others = [p for buys in moviesByUser if product in buys for p in buys]
    return dict(Counter(others))

def match(pid):
    return movies['title'][movies['title'].str.contains(pid)]


# In[77]:


pid = "Transformers (2007)"
if type(pid) is not int:
    pid=titletomovie[pid]
# print(match(pid))
n=20
# bought_with = bought_along(pid)
# top_bought=sorted(bought_with, key=lambda k:bought_with[k], reverse=True)[:n]
recommend=set(bought_with).intersection(similar_products(pid, n))
print(moviedict[pid], genres[pid])
movieidx.loc[list(recommend)].sort_values('rating', ascending=False).reset_index(drop=True)
# print(bought_with)


# In[ ]:




