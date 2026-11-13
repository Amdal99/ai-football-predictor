import streamlit as st
import math
import requests

st.set_page_config(
    page_title="AI Football Predictor",
    page_icon="⚽",
    layout="wide"
)

API_KEY = st.secrets["FOOTBALL_API_KEY"]
HEADERS = {"X-Auth-Token": API_KEY}
@st.cache_data(ttl=3600)
def hent_kamper(ligakode):
    url = f"https://api.football-data.org/v4/competitions/{ligakode}/matches"
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={"status": "SCHEDULED"},
            timeout=15
        )
        response.raise_for_status()
        return response.json().get("matches", [])
    except requests.RequestException as e:
        st.error(f"Kunne ikke hente kamper: {e}")
        return []


@st.cache_data(ttl=3600)
def hent_resultater(ligakode):
    url = f"https://api.football-data.org/v4/competitions/{ligakode}/matches"
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={"status": "FINISHED"},
            timeout=15
        )
        response.raise_for_status()
        return response.json().get("matches", [])
    except requests.RequestException as e:
        st.error(f"Kunne ikke hente resultater: {e}")
        return []


def beregn_lagstatistikk(kamper):
    statistikk = {}

    for kamp in kamper:
        hjemme = kamp["homeTeam"]["name"]
        borte = kamp["awayTeam"]["name"]
        resultat = kamp.get("score", {}).get("fullTime", {})

        hjemmemal = resultat.get("home")
        bortemal = resultat.get("away")

        if hjemmemal is None or bortemal is None:
            continue

        for lag in [hjemme, borte]:
            if lag not in statistikk:
                statistikk[lag] = {
                    "kamper": 0,
                    "scoret": 0,
                    "sluppet_inn": 0
                }

        statistikk[hjemme]["kamper"] += 1
        statistikk[hjemme]["scoret"] += hjemmemal
        statistikk[hjemme]["sluppet_inn"] += bortemal

        statistikk[borte]["kamper"] += 1
        statistikk[borte]["scoret"] += bortemal
        statistikk[borte]["sluppet_inn"] += hjemmemal

    for lag, tall in statistikk.items():
        antall = tall["kamper"]
        tall["snitt_scoret"] = tall["scoret"] / antall
        tall["snitt_sluttet_inn"] = tall["sluppet_inn"] / antall

    return statistikk


def finn_lagstatistikk(lagnavn, statistikk):
    return statistikk.get(lagnavn)

st.title("⚽ AI Football Predictor")
st.caption("Demoversjon – kun virtuelle penger")

leagues = {
    "Eliteserien": ["Viking", "Bodø/Glimt"],
    "Premier League": ["Arsenal", "Chelsea"],
    "Bundesliga": ["Bayern München", "Dortmund"],
    "2. Bundesliga": ["Schalke", "Hertha Berlin"]
}

league = st.selectbox("Velg liga", list(leagues))
home, away = leagues[league]


ligakoder = {
    "Premier League": "PL",
    "Bundesliga": "BL1",
    "2. Bundesliga": "BL2",
}



if league in ligakoder:
    historiske_kamper = hent_resultater(ligakoder[league])
    lagstatistikk = beregn_lagstatistikk(historiske_kamper)

    st.write(f"Historiske kamper hentet: {len(historiske_kamper)}")
    st.write(f"Antall lag med statistikk: {len(lagstatistikk)}")

    if lagstatistikk:
        st.write("Lag med historiske data:")
        st.write(list(lagstatistikk.keys())[:5])



if league in ligakoder:
    st.subheader("Kommende kamper")
    kamper = hent_kamper(ligakoder[league])

    if kamper:
        for kamp in kamper[:10]:
            hjemmelag = kamp["homeTeam"]["name"]
            bortelag = kamp["awayTeam"]["name"]
            dato = kamp["utcDate"][:10]
            hjemmestatistikk = finn_lagstatistikk(hjemmelag, lagstatistikk)
            
            bortestatistikk = finn_lagstatistikk(bortelag, lagstatistikk)

            st.write(f"{dato}: {hjemmelag} vs {bortelag}")
    else:
        st.info("Ingen kommende kamper tilgjengelig fra API-et.")
st.subheader(f"{home} vs {away}")

home_goals = st.slider(
    "Forventede hjemmemål", 0.2, 4.0, 1.7, 0.1
)
away_goals = st.slider(
    "Forventede bortemål", 0.2, 4.0, 1.1, 0.1
)

def poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)

p1 = px = p2 = 0.0
for h in range(16):
    for a in range(16):
        p = poisson(h, home_goals) * poisson(a, away_goals)
        if h > a:
            p1 += p
        elif h == a:
            px += p
        else:
            p2 += p

total = p1 + px + p2
p1, px, p2 = [p / total for p in (p1, px, p2)]

c1, c2, c3 = st.columns(3)
c1.metric("Hjemmeseier", f"{p1:.1%}")
c2.metric("Uavgjort", f"{px:.1%}")
c3.metric("Borteseier", f"{p2:.1%}")

st.subheader("📊 Oddsanalyse")
outcome = st.selectbox(
    "Velg utfall", ["Hjemmeseier", "Uavgjort", "Borteseier"]
)
odds = st.number_input(
    "Desimalodds", min_value=1.01, value=2.10, step=0.05
)

prob = {
    "Hjemmeseier": p1,
    "Uavgjort": px,
    "Borteseier": p2
}[outcome]

edge = prob * odds - 1
st.metric("Teoretisk forventet avkastning", f"{edge:.1%}")

if edge > 0:
    st.success("Modellen viser mulig verdi i oddsen.")
else:
    st.warning("Ingen positiv modellverdi ved denne oddsen.")

st.info(
    "Alle lag, forventede mål og odds er "
    "demonstrasjonsdata. Ikke bruk dette "
    "som grunnlag for ekte pengespill."
)
