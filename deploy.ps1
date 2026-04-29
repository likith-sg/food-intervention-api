gcloud config set project foodguard-494610
gcloud config set run/region asia-south1

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud run deploy food-intervention-api --source . --platform managed --region asia-south1 --allow-unauthenticated --port 8080 --memory 512Mi --cpu 1 --min-instances 0 --max-instances 2 --timeout 30 --set-env-vars="ENVIRONMENT=production"

$LIVE_URL = (gcloud run services describe food-intervention-api --platform managed --region asia-south1 --format 'value(status.url)')
Write-Host "LIVE URL: $LIVE_URL"
