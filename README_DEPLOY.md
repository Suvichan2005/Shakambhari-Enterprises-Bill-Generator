Deployment instructions for Cloud Run

1) Ensure you have the `gcloud` CLI authenticated and the project set:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2) Build and push using the provided script (replace PROJECT_ID):

```bash
chmod +x scripts/deploy_cloud_run.sh
./scripts/deploy_cloud_run.sh YOUR_PROJECT_ID
```

3) Alternatively use Cloud Build with the supplied `cloudbuild.yaml`:

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=_SERVICE_NAME=shakambhari-invoices-529104378195
```

Notes:
- The Cloud Run service name is `shakambhari-invoices-529104378195` in `asia-south1`.
- Ensure the GCP project has Cloud Run and Cloud Build APIs enabled and you have permission to deploy.
- The Docker image is built from `cloud/Dockerfile` and runs `app_cloud:app` with Gunicorn.
