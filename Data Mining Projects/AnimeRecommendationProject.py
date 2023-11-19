import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from collections import Counter
import re
import gc

# Load datasets
anime_data = pd.read_csv('/Users/emaleejimenez/Downloads/archive/anime.csv', low_memory=False)
anime_ratings = pd.read_csv('/Users/emaleejimenez/Downloads/archive/animelist.csv', low_memory=False)

anime_data = anime_data[['MAL_ID', 'Name', 'Score', 'Genres', 'Type', 'Episodes', 'Members']]
anime_data.rename(columns={'MAL_ID':"anime_id"},inplace=True)
anime_ratings.drop(anime_ratings.iloc[:,3:],axis=1,inplace=True)
anime_ratings.anime_id.nunique()
anime_ratings = anime_ratings.sample(frac=0.2)
anime_ratings.info()
anime_ratings.anime_id.nunique()
anime_complete = pd.merge(anime_data,anime_ratings,on='anime_id')
anime_complete=anime_complete.rename(columns={'rating':'user_rating','Score':'total_rating','Name':'anime_title'})
anime_complete.info()
anime_complete.isna().sum()

# Count the number of occurrences of each anime name
top_10_anime = anime_complete['anime_title'].value_counts().nlargest(10)
palette = sns.color_palette('rocket', len(top_10_anime))
# Create the bar chart
plt.bar(top_10_anime.index, top_10_anime.values, color=palette)

# Set the title and labels
plt.title('Top 10 Anime by User Rating Count')
plt.xlabel('Anime Name')
plt.ylabel('User Rating Count')

# Rotate the x-axis labels for better readability
plt.xticks(rotation=40, ha="right")

# Show the plot
plt.show()

top_10_anime = anime_complete.sort_values(by='Members', ascending=False).drop_duplicates(subset='anime_title').head(10)

palette = sns.color_palette('rocket', len(top_10_anime))

# Create a bar chart with the anime titles and the number of members
plt.bar(top_10_anime['anime_title'], top_10_anime['Members'],color=palette)

# Set the title and labels
plt.title('Top 10 Anime by Number of Members')
plt.xlabel('Anime Title')
plt.ylabel('Number of Members')

# Rotate the x-axis labels for better readability
plt.xticks(rotation=40,ha='right')

# Show the plot
plt.show()

# Create a list of genres by splitting and flattening the list
all_genres = sum(anime_data['Genres'].dropna().str.split(',').tolist(), [])

# Count the frequency of each genre
genre_counts = Counter(all_genres)

# Create a dataframe from the genre counts
genre_df = pd.DataFrame.from_dict(genre_counts, orient='index', columns=['Count']).sort_values('Count', ascending=False)

# Plot the top 10 genres
top_genres = genre_df.head(10)
plt.figure(figsize=(10,6))
sns.barplot(x=top_genres['Count'], y=top_genres.index, palette='rocket')
plt.title('Top 10 Most Popular Anime Genres')
plt.xlabel('Count')
plt.ylabel('Genre')
plt.show()

heatmap_df = pd.concat([anime_complete['total_rating'],anime_complete['user_rating'],anime_complete['Members']],axis=1)
heatmap_df['total_rating'] = pd.to_numeric(anime_complete['total_rating'], errors='coerce')
heatmap_df['user_rating'] = pd.to_numeric(anime_complete['user_rating'], errors='coerce')
correlation_matrix = heatmap_df[['Members', 'user_rating', 'total_rating']].corr()

# Plotting the heatmap
plt.figure(figsize=(10, 6))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
plt.title('Correlation between Members, User Rating, and Total Rating')
plt.show()

anime_features = anime_complete.copy()
anime_features.head()

anime_features.isnull().sum()

user_id_counts = anime_features['user_id'].value_counts()
user_id_counts

user_id_counts.describe()

# Keep only the rows for which the user_id appears at least 200 times
anime_features = anime_features[anime_features['user_id'].isin(user_id_counts[user_id_counts >= 100].index)]

anime_features.user_id.nunique()

def text_cleaning(text):
    # Compile the regular expressions only once
    replacements = {
        r'&quot;': '',
        r'.hack//': '',
        r'&#039;': '',
        r'A&#039;s': '',
        r'I&#039;': "I'",
        r'&amp;': 'and',
    }
    regex = re.compile("|".join(map(re.escape, replacements.keys())))
    return regex.sub(lambda match: replacements[match.group(0)], text)

anime_features['anime_title'] = anime_features['anime_title'].apply(text_cleaning)

anime_pivot=anime_features.pivot_table(index='anime_title',columns='user_id',values='user_rating').fillna(0)
anime_pivot.head()

from sklearn.feature_extraction.text import TfidfVectorizer

# Initialize the TfidfVectorizer with various parameters
tfv = TfidfVectorizer(min_df=3,  max_features=None, 
            strip_accents='unicode', analyzer='word',token_pattern=r'\w{1,}',
            ngram_range=(1, 3),
            stop_words = 'english')

# Fill NaN values in the 'Genres' column with an empty string
anime_data['Genres'] = anime_data['Genres'].fillna('')

# Split the 'Genres' column by comma and convert to string format
genres_str = anime_data['Genres'].str.split(',').astype(str)

# Use the TfidfVectorizer to transform the genres_str into a sparse matrix
tfv_matrix = tfv.fit_transform(genres_str)

# Print the shape of the sparse matrix
print(tfv_matrix.shape)

from sklearn.metrics.pairwise import sigmoid_kernel

# Compute the sigmoid kernel
sig = sigmoid_kernel(tfv_matrix, tfv_matrix)

# Create a Pandas Series object where the index is the anime names and the values are the indices in anime_data
indices = pd.Series(anime_data.index, index=anime_data['Name'])

# Remove duplicates in the index (i.e., duplicate anime names)
indices = indices.drop_duplicates()

def give_rec_cbf(title, sig=sig):
    # Get the index corresponding to anime title
    idx = indices[title]

    # Get the pairwsie similarity scores 
    sig_scores = list(enumerate(sig[idx]))

    # Sort the anime based on similarity scores
    sig_scores = sorted(sig_scores, key=lambda x: x[1], reverse=True)

    # Get the indices of top 10 most similar anime excluding the input anime
    anime_indices = [i[0] for i in sig_scores[1:11]]

    # Create dataframe of top 10 recommended anime
    top_anime = pd.DataFrame({
        'Anime name': anime_data['Name'].iloc[anime_indices].values,
        'Rating': anime_data['Score'].iloc[anime_indices].values
    })

    return top_anime

def recommend_anime_for_user(user_id, anime_features, anime_data, sig, indices):
    if user_id not in anime_features['user_id'].unique():
        return "User ID not found in the dataset."

    user_ratings = anime_features[anime_features['user_id'] == user_id]
    top_rated_anime_title = user_ratings.sort_values(by='user_rating', ascending=False)['anime_title'].iloc[0]
    return give_rec_cbf(top_rated_anime_title, sig=sig)

# Example usage:
users = {}

user_ids = [131988, 214221, 11010, 61205, 343118]

for user_id in user_ids:
    users[user_id] = recommend_anime_for_user(user_id, anime_features, anime_data, sig, indices)
    print(f"Recommendations for user {user_id}:", users[user_id])


gc.collect()