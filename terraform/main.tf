
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0" # or a later version
    }
  }
  backend "gcs" {
    bucket = "strava-terraform-state"
  }
}



provider "google" {
  credentials = var.gcp_sa_key
  project     = var.gcp_project_id
  region      = var.gcp_region
}



resource "google_artifact_registry_repository" "default" {
  location      = var.gcp_region
  repository_id = "strava"
  description   = "Docker repository"
  format        = "DOCKER"
}

resource "google_cloud_run_v2_service" "default" {
  name     = "strava"
  location = var.gcp_region

  template {

    containers {
      command = ["fastapi", "run", "./src/app/main.py"]
      args    = ["--host", "0.0.0.0", "--port", "8080"]
      image   = "${google_artifact_registry_repository.default.location}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.default.repository_id}/strava:${var.image_tag}"
      resources {
        cpu_idle          = true
        startup_cpu_boost = true
        limits = {
          cpu    = "4000m"
          memory = "2Gi"
        }
      }
      env {
        name  = "APPLICATION_URL"
        value = "https://strava-983811446432.africa-south1.run.app"
      }
      env {
        name = "STRAVA_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = "STRAVA_CLIENT_ID"
            version = "latest"
          }
        }
      }
      env {
        name = "STRAVA_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = "STRAVA_CLIENT_SECRET"
            version = "latest"
          }
        }
      }
      env {
        name = "PUSHBULLET_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "PUSHBULLET_API_KEY"
            version = "latest"
          }
        }
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "GEMINI_API_KEY"
            version = "latest"
          }
        }
      }
      env {
        name = "STRAVA_VERIFY_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "STRAVA_VERIFY_TOKEN"
            version = "latest"
          }
        }
      }
      env {
        name = "POSTGRES_CONNECTION_STRING"
        value_source {
          secret_key_ref {
            secret  = "POSTGRES_CONNECTION_STRING"
            version = "latest"
          }
        }
      }
      env {
        name = "ENCRYPTION_KEY"
        value_source {
          secret_key_ref {
            secret  = "ENCRYPTION_KEY"
            version = "latest"
          }
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

  }
  timeouts {}
}
