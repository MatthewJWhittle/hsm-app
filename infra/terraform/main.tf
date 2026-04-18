locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudtasks.googleapis.com",
    "firestore.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ])

  common_env = {
    GOOGLE_CLOUD_PROJECT = var.project_id
    STORAGE_BACKEND      = "gcs"
    GCS_OBJECT_PREFIX    = ""
    OPENAPI_ENABLED      = "true"
  }

  gcs_bucket_name = var.create_gcs_bucket ? google_storage_bucket.model_artifacts[0].name : var.gcs_bucket_name

  # Public HTTPS origins (no trailing slash). Set from `terraform output api_staging_uri` / `api_prod_uri`
  # after first apply — Terraform cannot reference a Cloud Run service's own .uri inside the same resource
  # without a dependency cycle (see infra/terraform/README.md).
  api_staging_public_trim = trimspace(var.api_staging_service_public_uri)
  api_prod_public_trim    = trimspace(var.api_prod_service_public_uri)
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "required" {
  for_each                   = local.required_services
  project                    = var.project_id
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_artifact_registry_repository" "backend" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository_id
  format        = "DOCKER"
  description   = "Docker images for hsm-app backend API."

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "model_artifacts" {
  count    = var.create_gcs_bucket ? 1 : 0
  project  = var.project_id
  name     = var.gcs_bucket_name
  location = var.gcs_bucket_location

  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = var.gcs_enable_versioning
  }

  cors {
    origin = [
      "https://hsm-dashboard-dev.web.app",
      "https://hsm-dashboard-dev.firebaseapp.com",
      "https://hsm-dashboard.web.app",
      "https://hsm-dashboard.firebaseapp.com",
    ]
    method = [
      "OPTIONS",
      "PUT",
    ]
    response_header = [
      "Content-Type",
      "x-goog-resumable",
      "x-goog-content-sha256",
    ]
    max_age_seconds = 3600
  }

  depends_on = [google_project_service.required]
}

resource "google_billing_budget" "mvp_monthly" {
  count           = var.create_budget_alerts && var.billing_account_id != null ? 1 : 0
  billing_account = var.billing_account_id
  display_name    = "hsm-app-mvp-monthly-budget"

  budget_filter {
    projects = ["projects/${data.google_project.current.number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_amount_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }

  threshold_rules {
    threshold_percent = 0.9
  }

  threshold_rules {
    threshold_percent = 1.0
  }

  all_updates_rule {
    monitoring_notification_channels = var.budget_notification_channels
    disable_default_iam_recipients   = false
    schema_version                   = "1.0"
  }
}

resource "google_firestore_database" "default" {
  count       = var.create_firestore_database ? 1 : 0
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "api_staging" {
  project      = var.project_id
  account_id   = "hsm-api-staging"
  display_name = "HSM API staging runtime"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "api_prod" {
  project      = var.project_id
  account_id   = "hsm-api-prod"
  display_name = "HSM API production runtime"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "titiler" {
  project      = var.project_id
  account_id   = "hsm-titiler"
  display_name = "HSM TiTiler runtime"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "api_staging_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_project_iam_member" "api_prod_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_prod.email}"
}

resource "google_storage_bucket_iam_member" "api_staging_storage_admin" {
  count  = var.create_gcs_bucket ? 1 : 0
  bucket = google_storage_bucket.model_artifacts[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_storage_bucket_iam_member" "api_prod_storage_admin" {
  count  = var.create_gcs_bucket ? 1 : 0
  bucket = google_storage_bucket.model_artifacts[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api_prod.email}"
}

resource "google_service_account_iam_member" "api_staging_token_creator_self" {
  service_account_id = google_service_account.api_staging.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_service_account_iam_member" "api_prod_token_creator_self" {
  service_account_id = google_service_account.api_prod.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.api_prod.email}"
}

# Background jobs (Cloud Tasks → Cloud Run worker). Runtime SAs enqueue tasks and
# call the API as OIDC identity; self run.invoker allows that OIDC token to invoke
# the same Cloud Run service that enqueued the task.
resource "google_cloud_tasks_queue" "jobs" {
  project  = var.project_id
  name     = var.cloud_tasks_queue_name
  location = var.cloud_tasks_queue_location

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "api_staging_cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_project_iam_member" "api_prod_cloudtasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.api_prod.email}"
}

resource "google_cloud_run_v2_service_iam_member" "api_staging_run_invoker_self" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api_staging.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_cloud_run_v2_service_iam_member" "api_prod_run_invoker_self" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api_prod.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api_prod.email}"
}

resource "google_storage_bucket_iam_member" "titiler_storage_viewer" {
  count  = var.create_gcs_bucket ? 1 : 0
  bucket = google_storage_bucket.model_artifacts[0].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.titiler.email}"
}

resource "google_secret_manager_secret_iam_member" "api_staging_secret_accessor" {
  project   = var.project_id
  secret_id = var.firebase_web_api_key_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_secret_manager_secret_iam_member" "api_prod_secret_accessor" {
  project   = var.project_id
  secret_id = var.firebase_web_api_key_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_prod.email}"
}


resource "google_cloud_run_v2_service" "api_staging" {
  name     = var.api_service_name_staging
  location = var.region
  ingress  = var.api_ingress

  template {
    service_account = google_service_account.api_staging.email
    timeout         = "${var.api_timeout_seconds}s"

    scaling {
      min_instance_count = var.api_min_instance_count
      max_instance_count = var.api_max_instance_count
    }

    containers {
      image = var.api_container_image_staging

      ports {
        container_port = var.api_container_port
      }

      resources {
        limits = {
          cpu    = var.api_cpu
          memory = var.api_memory
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = local.common_env.GOOGLE_CLOUD_PROJECT
      }
      env {
        name  = "STORAGE_BACKEND"
        value = local.common_env.STORAGE_BACKEND
      }
      env {
        name  = "GCS_BUCKET"
        value = local.gcs_bucket_name
      }
      env {
        name  = "GCS_OBJECT_PREFIX"
        value = local.common_env.GCS_OBJECT_PREFIX
      }
      env {
        name  = "GCS_SIGNED_URL_SERVICE_ACCOUNT"
        value = google_service_account.api_staging.email
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins_staging
      }
      env {
        name  = "CORS_ORIGIN_REGEX"
        value = var.cors_origin_regex_staging
      }
      env {
        name  = "OPENAPI_ENABLED"
        value = local.common_env.OPENAPI_ENABLED
      }
      env {
        name  = "TITILER_URL"
        value = google_cloud_run_v2_service.titiler.uri
      }
      env {
        name = "FIREBASE_WEB_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.firebase_web_api_key_secret_name
            version = "latest"
          }
        }
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }

      # Background jobs: infra-owned (queue + IAM + env). CI deploy only swaps the container image.
      env {
        name  = "JOB_QUEUE_BACKEND"
        value = var.api_job_queue_backend_staging
      }
      env {
        name  = "CLOUD_TASKS_LOCATION"
        value = var.cloud_tasks_queue_location
      }
      env {
        name  = "CLOUD_TASKS_QUEUE_ID"
        value = var.cloud_tasks_queue_name
      }
      env {
        name  = "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL"
        value = google_service_account.api_staging.email
      }
      dynamic "env" {
        for_each = length(local.api_staging_public_trim) > 0 ? [1] : []
        content {
          name  = "JOB_WORKER_URL"
          value = "${local.api_staging_public_trim}/api/internal/jobs/run"
        }
      }
      dynamic "env" {
        for_each = length(local.api_staging_public_trim) > 0 ? [1] : []
        content {
          name  = "CLOUD_TASKS_OIDC_AUDIENCE"
          value = local.api_staging_public_trim
        }
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    # CI/CD deploys new API revisions outside Terraform.
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_project_iam_member.api_staging_firestore_user,
  ]
}

resource "google_cloud_run_v2_service" "api_prod" {
  name     = var.api_service_name_prod
  location = var.region
  ingress  = var.api_ingress

  template {
    service_account = google_service_account.api_prod.email
    timeout         = "${var.api_timeout_seconds}s"

    scaling {
      min_instance_count = var.api_min_instance_count
      max_instance_count = var.api_max_instance_count
    }

    containers {
      image = var.api_container_image_prod

      ports {
        container_port = var.api_container_port
      }

      resources {
        limits = {
          cpu    = var.api_cpu
          memory = var.api_memory
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = local.common_env.GOOGLE_CLOUD_PROJECT
      }
      env {
        name  = "STORAGE_BACKEND"
        value = local.common_env.STORAGE_BACKEND
      }
      env {
        name  = "GCS_BUCKET"
        value = local.gcs_bucket_name
      }
      env {
        name  = "GCS_OBJECT_PREFIX"
        value = local.common_env.GCS_OBJECT_PREFIX
      }
      env {
        name  = "GCS_SIGNED_URL_SERVICE_ACCOUNT"
        value = google_service_account.api_prod.email
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins_prod
      }
      env {
        name  = "CORS_ORIGIN_REGEX"
        value = var.cors_origin_regex_prod
      }
      env {
        name  = "OPENAPI_ENABLED"
        value = local.common_env.OPENAPI_ENABLED
      }
      env {
        name  = "TITILER_URL"
        value = google_cloud_run_v2_service.titiler.uri
      }
      env {
        name = "FIREBASE_WEB_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.firebase_web_api_key_secret_name
            version = "latest"
          }
        }
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }

      env {
        name  = "JOB_QUEUE_BACKEND"
        value = var.api_job_queue_backend_prod
      }
      env {
        name  = "CLOUD_TASKS_LOCATION"
        value = var.cloud_tasks_queue_location
      }
      env {
        name  = "CLOUD_TASKS_QUEUE_ID"
        value = var.cloud_tasks_queue_name
      }
      env {
        name  = "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL"
        value = google_service_account.api_prod.email
      }
      dynamic "env" {
        for_each = length(local.api_prod_public_trim) > 0 ? [1] : []
        content {
          name  = "JOB_WORKER_URL"
          value = "${local.api_prod_public_trim}/api/internal/jobs/run"
        }
      }
      dynamic "env" {
        for_each = length(local.api_prod_public_trim) > 0 ? [1] : []
        content {
          name  = "CLOUD_TASKS_OIDC_AUDIENCE"
          value = local.api_prod_public_trim
        }
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    # CI/CD deploys new API revisions outside Terraform.
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_project_iam_member.api_prod_firestore_user,
  ]
}

resource "google_cloud_run_v2_service" "titiler" {
  name     = var.titiler_service_name
  location = var.region
  ingress  = var.titiler_ingress

  template {
    service_account = google_service_account.titiler.email
    timeout         = "${var.titiler_timeout_seconds}s"

    scaling {
      min_instance_count = var.titiler_min_instance_count
      max_instance_count = var.titiler_max_instance_count
    }

    containers {
      image = var.titiler_container_image

      ports {
        container_port = var.titiler_container_port
      }

      resources {
        limits = {
          cpu    = var.titiler_cpu
          memory = var.titiler_memory
        }
      }

      env {
        name  = "TITILER_CACHE_DISABLE"
        value = "true"
      }
      env {
        name  = "TITILER_CACHE_TYPE"
        value = "null"
      }
      env {
        name  = "GDAL_DISABLE_READDIR_ON_OPEN"
        value = "FALSE"
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    google_project_service.required,
    google_storage_bucket_iam_member.titiler_storage_viewer,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "api_staging_invoker" {
  count    = var.allow_unauthenticated_api ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api_staging.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "api_prod_invoker" {
  count    = var.allow_unauthenticated_api ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api_prod.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "titiler_invoker" {
  count    = var.allow_unauthenticated_titiler ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.titiler.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

check "staging_jobs_need_public_api_uri" {
  assert {
    condition     = !contains(["cloud_tasks", "direct"], var.api_job_queue_backend_staging) || length(local.api_staging_public_trim) > 0
    error_message = "api_job_queue_backend_staging is ${var.api_job_queue_backend_staging}: set api_staging_service_public_uri to the staging API HTTPS origin (no trailing slash), e.g. from terraform output api_staging_uri after the first apply."
  }
}

check "prod_jobs_need_public_api_uri" {
  assert {
    condition     = !contains(["cloud_tasks", "direct"], var.api_job_queue_backend_prod) || length(local.api_prod_public_trim) > 0
    error_message = "api_job_queue_backend_prod is ${var.api_job_queue_backend_prod}: set api_prod_service_public_uri to the production API HTTPS origin (no trailing slash), e.g. from terraform output api_prod_uri."
  }
}
