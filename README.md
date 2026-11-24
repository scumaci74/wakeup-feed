# Wake Up – Feed RSS personale

Feed RSS personale non ufficiale per **Wake Up – La rassegna che sveglia gli italiani** di Antonio Fraschilla, pubblicato da Repubblica.

## Fonte

Endpoint JSON della rubrica Repubblica (`JSON_URL` in `update_feed.py`), individuato nel browser e verificato il 24 novembre 2026. Contiene `title`, `audio_url`, `original_id`, `pub_date`, `duration`, `image`.

## Funzionamento

- `update_feed.py` legge il JSON, raccoglie fino a cinque pagine, conserva nel `feed.xml` le puntate già presenti e aggiunge quelle nuove.
- Quando non ci sono puntate nuove non cambia il feed.
- `.github/workflows/update-feed.yml` avvia lo script manualmente e riprova fino a tre volte se una richiesta fallisce; non ha scheduler interno.
- Gli aggiornamenti programmati saranno affidati a cron-job.org dopo il collaudo.

## Primo collaudo

1. Crea il repository pubblico `scumaci74/wakeup-feed` su GitHub.
2. Carica `update_feed.py`, `requirements.txt`, `README.md` nella root e il workflow nel percorso `.github/workflows/update-feed.yml`.
3. GitHub Actions → **Aggiorna Feed Wake Up** → **Run workflow** → branch `main`.
4. Verifica il run e l'esistenza di `feed.xml`; se il JSON viene bloccato ai runner GitHub, leggere gli errori prima di procedere.
5. Settings → Pages → Deploy from a branch → `main` → `/ (root)`.
6. Aggiungi a Pocket Casts l'URL `https://scumaci74.github.io/wakeup-feed/feed.xml`.
7. Solo a collaudo riuscito configura cron-job.org con una chiamata `POST` a GitHub Actions.

## Nota

I collegamenti audio sono pubblicamente raggiungibili nella verifica effettuata il 24 novembre 2026; ciò non garantisce che la disponibilità rimanga invariata. Il feed non è ufficiale e non ospita copie dei file audio. La copertina del canale usa l'immagine del primo episodio individuato, mentre le copertine individuali provengono dal JSON.
