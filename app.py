
import json
import re

import streamlit as st
from groq import Groq
from pydantic import BaseModel, Field


# =====================================================
# 1. INSTELLINGEN
# =====================================================

st.set_page_config(
    st.image("logo.png", width=150),
    page_title="Studiekeuze Coach",
    page_icon="🎓",
    layout="centered"
)

MODEL = "openai/gpt-oss-20b"

client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)


# =====================================================
# 2. LEERLINGPROFIEL
# =====================================================

class StudentProfile(BaseModel):

    schoolniveau: str = ""
    leerjaar: str = ""

    interesses: list[str] = Field(default_factory=list)
    favoriete_vakken: list[str] = Field(default_factory=list)
    minder_leuke_vakken: list[str] = Field(default_factory=list)
    sterke_punten: list[str] = Field(default_factory=list)
    vaardigheden: list[str] = Field(default_factory=list)

    persoonlijkheid: str = ""
    werkvoorkeur: str = ""

    toekomstwensen: list[str] = Field(default_factory=list)
    belangrijke_waarden: list[str] = Field(default_factory=list)
    opleidingsvoorkeuren: list[str] = Field(default_factory=list)
    aandachtspunten: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):

    antwoord: str
    profiel: StudentProfile


# =====================================================
# 3. SYSTEEMPROMPT
# =====================================================

SYSTEM_PROMPT = """
Je bent een vriendelijke, deskundige en betrokken
Nederlandse studiekeuzecoach voor leerlingen in het
voortgezet onderwijs.

Je begeleidt leerlingen van vmbo, havo en vwo.

DOEL:
Help leerlingen ontdekken welke vervolgopleidingen,
studierichtingen en beroepen bij hen passen.

GESPREKSREGELS:

1. Je bent al bezig met een lopend gesprek.
2. Begin nooit opnieuw met een kennismaking.
3. Reageer altijd op het laatste bericht van de leerling.
4. Geef een korte, natuurlijke reactie.
5. Herhaal nooit letterlijk het antwoord.
6. Stel maximaal één relevante vervolgvraag.
7. Vraag niet opnieuw naar informatie die al bekend is.
8. Gebruik eerdere antwoorden om vervolgvragen te bepalen.
9. Verzin geen eigenschappen, interesses of ervaringen.
10. Leid geen eigenschappen af uit het schoolniveau.
11. Gebruik begrijpelijk Nederlands.
12. Wees positief, geduldig en niet-oordelend.
13. Geef de leerling ruimte om twijfels te uiten.
14. Stel in ieder antwoord dat je geeft een vraag
15. Wanneer je merkt dat je steeds met dezelfde vragen of opmerkingen reageert, begin over een nieuw onderwerp.

ONDERWERPEN DIE JE ONDERZOEKT:

- Interesses en hobby's.
- Favoriete schoolvakken.
- Minder leuke schoolvakken.
- Sterke punten.
- Vaardigheden en talenten.
- Persoonlijkheid en voorkeuren.
- Praktisch, theoretisch, creatief of sociaal werken.
- Toekomstwensen.
- Gewenste werkomgeving.
- Belangrijke persoonlijke waarden.

PROFIEL:

Je ontvangt bij iedere beurt het bestaande leerlingprofiel.

Werk dit profiel bij na ieder antwoord.

Regels:
- Bewaar eerder verzamelde informatie.
- Voeg nieuwe informatie toe.
- Verwijder geen informatie zonder reden.
- Gebruik lege velden als informatie ontbreekt.
- Bewaar alleen informatie die de leerling zelf heeft verteld.
- Verzin geen informatie.

STUDIEKEUZE:

Wanneer voldoende informatie is verzameld,
geef je een persoonlijk studiekeuzeadvies.

Het advies bevat:
1. Een samenvatting van het leerlingprofiel.
2. Drie tot vijf mogelijke studierichtingen.
3. Waarom deze richtingen mogelijk passen.
4. Mogelijke vervolgopleidingen.
5. Bijbehorende beroepen.
6. Wat de leerling verder kan onderzoeken.
7. Concrete vervolgstappen.

Maak onderscheid tussen vmbo, mbo, havo, hbo en wo.

Geef geen ongecontroleerde toelatingseisen.
Maak duidelijk dat opleidingen suggesties zijn
en geen definitieve beoordeling.

BELANGRIJK:

Als er onvoldoende informatie is verzameld,
stel dan een gerichte vervolgvraag.

Geef geen studiekeuzeadvies voordat er voldoende
informatie beschikbaar is.

Als de gebruiker over een ander onderwerp begint te vertellen, leid ze vriendelijk terug naar een gesprek over hun studiekeuze.

Houd je aan alle gespreksregels bij elk antwoord die je geeft.

Wanneer de gebruiker een antwoord heeft gegeven op een specifieke vraag dient deze vraag nergens in het gesprek opnieuw gesteld te worden.



LENGTE VAN ANTWOORDEN:

- Normaal gesproken 2 tot 4 zinnen.
- Bij vragen over een opleiding mag je uitgebreider antwoorden.
- Geef alleen informatie die relevant is.
- Houd je antwoorden overzichtelijk.

JSON:

- Geef uitsluitend een geldig JSON-object terug.
- Gebruik de velden antwoord en profiel.
- Vul alle profielvelden in.
- Gebruik lege lijsten en lege teksten als informatie ontbreekt.
- Sluit het JSON-object volledig af.
"""


# =====================================================
# 4. SESSIE INITIALISEREN
# =====================================================

def initialize_session():

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "profile" not in st.session_state:
        st.session_state.profile = StudentProfile()

    if "started" not in st.session_state:
        st.session_state.started = False


initialize_session()


# =====================================================
# 5. GESPREK STARTEN
# =====================================================

def start_conversation():

    st.session_state.started = True

    welcome_message = (
        "Hoi! Welkom bij jouw persoonlijke studiekeuzecoach! "
        "Ik ga je helpen ontdekken welke opleidingen en "
        "studierichtingen bij jou zouden kunnen passen. "
        "We doen dit stap voor stap. Er zijn geen goede of "
        "foute antwoorden. Om te beginnen: op welk "
        "schoolniveau zit je en in welk leerjaar?"
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome_message
    })


# =====================================================
# 6. PROFIEL BIJWERKEN
# =====================================================

def update_profile_from_message(user_message):

    message = user_message.lower()

    schoolniveaus = ["vmbo", "havo", "vwo"]

    for niveau in schoolniveaus:

        if re.search(rf"\b{niveau}\b", message):

            st.session_state.profile.schoolniveau = niveau.upper()
            break

    match = re.search(
        r"\b(?:leerjaar|klas|jaar)\s*([1-6])\b",
        message
    )

    if not match:

        match = re.search(
            r"\b([1-6])\s*(?:vmbo|havo|vwo)\b",
            message
        )

    if match:

        st.session_state.profile.leerjaar = match.group(1)


# =====================================================
# 7. PROFIELEN SAMENVOEGEN
# =====================================================

def merge_profiles(old_profile, new_profile):

    old_data = old_profile.model_dump()
    new_data = new_profile.model_dump()

    for key in old_data:

        if isinstance(old_data[key], list):

            combined = old_data[key] + new_data[key]

            new_data[key] = list(dict.fromkeys(combined))

        elif isinstance(old_data[key], str):

            if not new_data[key]:
                new_data[key] = old_data[key]

    return StudentProfile(**new_data)


# =====================================================
# 8. ANTWOORD GENEREREN MET GROQ
# =====================================================

def generate_response(user_message):

    if not user_message.strip():
        return None

    try:

        # Profiel bijwerken met schoolinformatie
        update_profile_from_message(user_message)

        # Huidig profiel ophalen
        current_profile = st.session_state.profile.model_dump()

        instructions = (
            SYSTEM_PROMPT
            + "\n\nHUIDIG LEERLINGPROFIEL:\n"
            + json.dumps(
                current_profile,
                ensure_ascii=False
            )
            + """

EXTRA INSTRUCTIES:

- Reageer op het nieuwste bericht van de leerling.
- Begin niet opnieuw met een kennismaking.
- Bevestig kort wat de leerling vertelt.
- Stel maximaal één relevante vervolgvraag.
- Gebruik het bestaande profiel.
- Bewaar eerder verzamelde informatie.
- Geef uitsluitend de gevraagde JSON-structuur terug.
"""
        )

        # Gespreksgeschiedenis samenstellen
        conversation = [
            {
                "role": "system",
                "content": instructions
            }
        ]

        conversation.extend(
            st.session_state.messages[-6:]
        )

        conversation.append({
            "role": "user",
            "content": user_message
        })

        # Groq API aanroepen
        response = client.chat.completions.create(
            model=MODEL,
            messages=conversation,
            response_format={
                "type": "json_object"
            },
            temperature=0.2,
            max_completion_tokens=1500
        )

        # Antwoord ophalen
        raw_response = response.choices[0].message.content

        print("\n========== GROQ RESPONS ==========")
        print(raw_response)
        print("==================================\n")

        if not raw_response:
            raise ValueError("Het AI-model heeft geen antwoord gegeven.")

        # JSON verwerken
        try:

            result = ChatResponse.model_validate_json(
                raw_response
            )

        except Exception as error:

            print("JSON-verwerkingsfout:", repr(error))
            print("Ontvangen antwoord:", repr(raw_response))

            st.error(
                "De chatbot heeft een onvolledig antwoord gegenereerd. "
                "Probeer je vraag nogmaals."
            )

            return None

        # Controleren of het model letterlijk herhaalt
        if (
            result.antwoord.strip().casefold()
            == user_message.strip().casefold()
        ):

            st.warning(
                "De chatbot heeft je antwoord herhaald. "
                "Probeer het nogmaals."
            )

            return None

        # Profielen samenvoegen
        updated_profile = merge_profiles(
            st.session_state.profile,
            result.profiel
        )

        st.session_state.profile = updated_profile

        # Gebruikersbericht opslaan
        st.session_state.messages.append({
            "role": "user",
            "content": user_message
        })

        # Antwoord opslaan
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.antwoord
        })

        return result.antwoord

    except Exception as error:

        st.error(
            "Er is iets misgegaan bij het verwerken "
            "van je bericht."
        )

        st.code(str(error))

        print("Groq-fout:", repr(error))

        return None


# =====================================================
# 9. SESSIE VERWIJDEREN
# =====================================================

def delete_session():

    for key in [
        "messages",
        "profile",
        "started"
    ]:

        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


# =====================================================
# 10. STREAMLIT INTERFACE
# =====================================================

st.title("Mijn Studiekeuze Coach")

st.write(
    "Ontdek welke vervolgopleiding bij jouw "
    "interesses, talenten en toekomstwensen past."
)

st.info(
    "Je profiel wordt alleen tijdens deze actieve "
    "sessie bijgehouden. Deel geen persoonlijke "
    "identificerende gegevens."
)


# =====================================================
# 11. ZIJBALK: LEERLINGPROFIEL
# =====================================================

with st.sidebar:

    st.header("👤 Leerlingprofiel")

    profile = st.session_state.profile

    st.write("**Schoolniveau**")
    st.write(profile.schoolniveau or "Nog niet bekend")

    st.write("**Leerjaar**")
    st.write(profile.leerjaar or "Nog niet bekend")

    st.divider()

    st.write("**Interesses**")

    if profile.interesses:
        for item in profile.interesses:
            st.write(f"- {item}")
    else:
        st.write("Nog niet bekend")

    st.write("**Favoriete vakken**")

    if profile.favoriete_vakken:
        for item in profile.favoriete_vakken:
            st.write(f"- {item}")
    else:
        st.write("Nog niet bekend")

    st.write("**Minder leuke vakken**")

    if profile.minder_leuke_vakken:
        for item in profile.minder_leuke_vakken:
            st.write(f"- {item}")
    else:
        st.write("Nog niet bekend")

    st.write("**Sterke punten**")

    if profile.sterke_punten:
        for item in profile.sterke_punten:
            st.write(f"- {item}")
    else:
        st.write("Nog niet bekend")

    st.write("**Vaardigheden**")

    if profile.vaardigheden:
        for item in profile.vaardigheden:
            st.write(f"- {item}")
    else:
        st.write("Nog niet bekend")

    st.write("**Toekomstwensen**")

    if profile.toekomstwensen:
        for item in profile.toekomstwensen:
            st.write(f"- {item}")
    else:
        st.write("Nog niet bekend")

    st.divider()

    if st.button(
        "Gesprek beëindigen en gegevens verwijderen",
        use_container_width=True
    ):

        delete_session()


# =====================================================
# 12. CHATVENSTER
# =====================================================

if not st.session_state.started:

    st.subheader("Welkom!")

    st.write(
        "Klik hieronder om jouw studiekeuzegesprek "
        "te beginnen."
    )

    if st.button(
        "Start mijn studiekeuzegesprek",
        use_container_width=True
    ):

        start_conversation()
        st.rerun()

else:

    # Eerdere berichten weergeven
    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

    # Invoer van de leerling
    user_input = st.chat_input(
        "Typ hier jouw antwoord..."
    )

    if user_input:

        with st.spinner("Even nadenken..."):

            answer = generate_response(user_input)

        if answer:
            st.rerun()


# =====================================================
# 13. VOETTEKST
# =====================================================

st.divider()

st.caption(
    "Studiekeuze Coach | AI-ondersteund advies. "
    "De leerling blijft zelf verantwoordelijk "
    "voor de uiteindelijke studiekeuze."
)
