@st.cache_data(ttl=600)
def get_matches(data_alvo):
    try:
        url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{data_alvo}"
        data = requests.get(url, headers=HEADERS).json()

        matches = []

        for event in data.get("events", []):
            try:
                # NÃO filtrar por timestamp (isso estava quebrando tudo)

                matches.append({
                    "home_id": event["homeTeam"]["id"],
                    "away_id": event["awayTeam"]["id"],
                    "home": event["homeTeam"]["name"],
                    "away": event["awayTeam"]["name"],
                    "tournament": event["tournament"]["name"],
                    "country": event["tournament"]["category"]["name"]
                })

            except:
                continue

        return matches

    except:
        return []
