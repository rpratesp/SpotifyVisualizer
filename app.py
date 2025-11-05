import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import plotly.express as px

# Âmbito de acesso aos dados do usuário
SCOPE = "user-top-read"

# Read the information that we store in the streamlit secrets
CLIENT_ID = st.secrets["SPOTIPY_CLIENT_ID"]
CLIENT_SECRET = st.secrets["SPOTIPY_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["SPOTIPY_REDIRECT_URI"]

# Set up an OAuth object that controls the Spotify login process
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotifycache"  # Optional, save the access token in between, so that we don’t have to log in again every time we load
)

# Define the title of our web app
st.title("🎵 Visualizador Retrospectiva Pessoal Anual do Spotify RPP")

# 1. Define that Streamlit reads the parameters from the URL
query_params = st.experimental_get_query_params()
code = query_params.get("code")

# 2. Define the access token
if "token_info" not in st.session_state:
    if code:
        # Exchange the code for a token
        token_info = sp_oauth.get_access_token(code[0], as_dict=True)
        # Save the token 
        st.session_state["token_info"] = token_info
        # Após uma troca de tokens bem-sucedida, realize um redirecionamento para remover os parâmetros de consulta.
        st.experimental_set_query_params()
    else:
        token_info = None
else:
    token_info = st.session_state["token_info"] # If a token has already been saved, we use the saved one

# 3. If no token is available or the token has expired
if not token_info or sp_oauth.is_token_expired(token_info):
    # Create a login URL, show the user a link to log in to Spotify
    auth_url = sp_oauth.get_authorize_url()
    st.write("Faça login no Spotify para visualizar seus dados:")
    st.markdown(f"[Spotify Login]({auth_url})", unsafe_allow_html=True)
    # Stop the app here until the user is logged in
    st.stop()

# 4. Leia o token de token_info
access_token = token_info["access_token"]

# 5. Inicialize o cliente Spotify com um token válido
sp = spotipy.Spotify(auth=access_token)

# --- A partir daqui, seu código fará chamadas à API do Spotify ---

time_range = st.selectbox("Período", ["short_term", "medium_term", "long_term"])

top_tracks = sp.current_user_top_tracks(limit=10, time_range=time_range)

track_names = [t["name"] for t in top_tracks["items"]]
popularities = [t["popularity"] for t in top_tracks["items"]]

df = pd.DataFrame({
    "Track": track_names,
    "Popularity": popularities
})

st.subheader("📋 Suas músicas favoritas")
st.dataframe(df)

fig = px.bar(df, x="Popularity", y="Track", orientation="h",
             title="Popularidade das suas melhores músicas", color="Popularity", height=400)
st.plotly_chart(fig, use_container_width=True)

st.subheader("🎤 Distribuição dos seus gêneros favoritos")

top_artists = sp.current_user_top_artists(limit=20, time_range=time_range)
genre_list = []
for artist in top_artists["items"]:
    genre_list.extend(artist["genres"])

genre_counts = pd.Series(genre_list).value_counts().head(10)

fig2 = px.pie(values=genre_counts.values, names=genre_counts.index,
              title="Seus gêneros mais frequentes", hole=0.4)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("📅 Ano de lançamento das suas melhores músicas – Clássicos ou sucessos das paradas?")

years = []
track_info = []

for track in top_tracks["items"]:
    release_date = track["album"]["release_date"]
    year = release_date[:4]
    years.append(int(year))
    track_info.append({
        "Track": track["name"],
        "Artist": track["artists"][0]["name"],
        "Album": track["album"]["name"],
        "Release Year": int(year),
        "Popularity": track["popularity"]
    })

df_years = pd.DataFrame(track_info)

fig3 = px.histogram(df_years, x="Release Year", nbins=len(set(years)),
                    title="Anos de lançamento das suas melhores músicas", color="Release Year")
st.plotly_chart(fig3, use_container_width=True)

csv_data = df_years.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📄 Baixe o arquivo CSV com os dados das músicas",
    data=csv_data,
    file_name="top_tracks_by_year.csv",
    mime="text/csv"
)
