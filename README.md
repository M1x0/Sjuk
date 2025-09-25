# Sjuk Autonomous Organization

Detta projekt startar en helt virtuell organisation bestående av samverkande AI-agenter som driver egna projekt, hanterar ekonomi och reagerar på kaos. Systemet körs som en FastAPI-applikation med en dashboard där man kan följa all aktivitet i realtid.

## Funktioner

- **Rollbaserade AI-agenter**: CEO, HR, Finance, Dev-team och Chaos-bot kommunicerar via en gemensam chatt som sparas i SQLite.
- **Projektlivscykel**: CEO pitchar idéer, Finance budgeterar, Dev-botar producerar kodsnuttar och projekt kan lyckas eller misslyckas baserat på resurser och störningar.
- **Kaos-händelser**: Chaos-bot triggar slumpmässiga händelser som fusk-skandaler, konkurrenter och krypto-krascher som kräver respons från organisationen.
- **Självlärande**: Misslyckade projekt loggas och påverkar framtida beslutsvikter. HR kan förstärka eller nedmontera dev-teamet.
- **Dashboard**: Visar antal agenter, aktiva projekt, ekonomisk historik och live-chat. Du kan även intervjua valfri AI-agent.

## Kom igång

### Förutsättningar

- Docker (för att köra hela miljön isolerat)

### Bygg och starta

```bash
docker build -t sjuk-org .
docker run --rm -p 8000:8000 sjuk-org
```

Öppna sedan [http://localhost:8000](http://localhost:8000) i din webbläsare för att se dashboarden.

## Struktur

```
src/virtual_org/
├── app.py              # FastAPI-app och API-endpoints
├── agents.py           # Agentbeteenden för CEO/HR/Finance/Dev/Chaos
├── database.py         # SQLite-hantering av meddelanden, projekt, finanser
├── organization.py     # Kärnlogiken för simuleringen och beslutsfattande
└── static/             # Frontend (HTML, CSS, JS) för dashboarden
```

När containern startar initieras databasen och simuleringen körs kontinuerligt i bakgrunden. Dashboarden uppdateras var fjärde sekund.

## Interaktion

- **Real-tidschat**: Alla agentmeddelanden sparas i databasen och visas i UI.
- **Intervjuer**: I dashboarden kan du välja en agent, ställa en fråga och få ett svar direkt i chatten.
- **Historik**: Alla data ligger i `data/org.db` (SQLite) och kan inspekteras även efter körning.

## Vidareutveckling

- Lägg till fler agentroller eller externa API-integrationer.
- Bygg ut beslutsmodellerna med maskininlärning baserad på loggdata.
- Använd WebSockets för ännu tätare realtidsuppdateringar.
