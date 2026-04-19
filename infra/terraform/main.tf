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

  # Cloud Tasks service agent (needs serviceAccountUser on OIDC SAs for task HTTP auth).
  cloudtasks_sa_email = "service-${data.google_project.current.number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"

  common_env = {
    GOOGLE_CLOUD_PROJECT = var.project_id
    STORAGE_BACKEND      = "gcs"
    GCS_OBJECT_PREFIX    = ""
    OPENAPI_ENABLED      = "true"
  }

  gcs_bucket_name = var.create_gcs_bucket ? google_storage_bucket.model_artifacts[0].name : var.gcs_bucket_name
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

# --- Background worker (Cloud Tasks targets) ---------------------------------

resource "google_service_account" "worker_staging" {
  project      = var.project_id
  account_id   = "hsm-worker-staging"
  display_name = "HSM background worker staging"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "worker_prod" {
  project      = var.project_id
  account_id   = "hsm-worker-prod"
  display_name = "HSM background worker production"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "tasks_oidc_staging" {
  project      = var.project_id
  account_id   = "hsm-tasks-oidc-staging"
  display_name = "Cloud Tasks OIDC to staging worker"

  depends_on = [google_project_service.required]
}

resource "google_service_account" "tasks_oidc_prod" {
  project      = var.project_id
  account_id   = "hsm-tasks-oidc-prod"
  display_name = "Cloud Tasks OIDC to production worker"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "worker_staging_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.worker_staging.email}"
}

resource "google_project_iam_member" "worker_prod_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.worker_prod.email}"
}

# Bucket-scoped objectAdmin (not roles/storage.admin on the whole project).
resource "google_storage_bucket_iam_member" "worker_staging_storage_admin" {
  count  = var.create_gcs_bucket ? 1 : 0
  bucket = google_storage_bucket.model_artifacts[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.worker_staging.email}"
}

resource "google_storage_bucket_iam_member" "worker_prod_storage_admin" {
  count  = var.create_gcs_bucket ? 1 : 0
  bucket = google_storage_bucket.model_artifacts[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.worker_prod.email}"
}

# GitHub Actions → Cloud Run: deploy identity must be able to actAs each service's runtime SA.
resource "google_service_account_iam_member" "github_deploy_actas_worker_staging" {
  count              = var.github_deploy_service_account_email != null ? 1 : 0
  service_account_id = google_service_account.worker_staging.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.github_deploy_service_account_email}"
}

resource "google_service_account_iam_member" "github_deploy_actas_worker_prod" {
  count              = var.github_deploy_service_account_email != null ? 1 : 0
  service_account_id = google_service_account.worker_prod.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.github_deploy_service_account_email}"
}

resource "google_cloud_tasks_queue" "background_staging" {
  name     = var.cloud_tasks_queue_staging_id
  location = var.region
  project  = var.project_id

  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s"
    min_backoff        = "10s"
    max_backoff        = "300s"
    max_doublings      = 4
  }

  rate_limits {
    max_dispatches_per_second = 5
    max_concurrent_dispatches = 2
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_tasks_queue" "background_prod" {
  name     = var.cloud_tasks_queue_prod_id
  location = var.region
  project  = var.project_id

  retry_config {
    max_attempts       = 5
    max_retry_duration = "3600s"
    min_backoff        = "10s"
    max_backoff        = "300s"
    max_doublings      = 4
  }

  rate_limits {
    max_dispatches_per_second = 10
    max_concurrent_dispatches = 3
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_tasks_queue_iam_member" "api_staging_enqueuer" {
  project  = var.project_id
  location = google_cloud_tasks_queue.background_staging.location
  name     = google_cloud_tasks_queue.background_staging.name
  role     = "roles/cloudtasks.enqueuer"
  member   = "serviceAccount:${google_service_account.api_staging.email}"
}

resource "google_cloud_tasks_queue_iam_member" "api_prod_enqueuer" {
  project  = var.project_id
  location = google_cloud_tasks_queue.background_prod.location
  name     = google_cloud_tasks_queue.background_prod.name
  role     = "roles/cloudtasks.enqueuer"
  member   = "serviceAccount:${google_service_account.api_prod.email}"
}

resource "google_service_account_iam_member" "tasks_oidc_staging_actas" {
  service_account_id = google_service_account.tasks_oidc_staging.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.cloudtasks_sa_email}"
}

resource "google_service_account_iam_member" "tasks_oidc_prod_actas" {
  service_account_id = google_service_account.tasks_oidc_prod.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.cloudtasks_sa_email}"
}

# Workers use the same ingress class as the API. Cloud Tasks invokes the service URL over
# HTTPS; INGRESS_TRAFFIC_ALL is the standard pairing. Access control is IAM: only the Tasks
# OIDC service accounts receive roles/run.invoker (see worker_*_tasks_invoker below).
resource "google_cloud_run_v2_service" "worker_staging" {
  name     = var.worker_service_name_staging
  location = var.region
  ingress  = var.api_ingress

  template {
    service_account = google_service_account.worker_staging.email
    timeout         = "${var.worker_timeout_seconds_staging}s"

    scaling {
      min_instance_count = 0
      max_instance_count = var.worker_max_instances_staging
    }

    containers {
      image = var.api_container_image_staging

      ports {
        container_port = var.worker_container_port
      }

      command = ["uv"]
      args = [
        "run", "uvicorn", "hsm_worker.main:app",
        "--host", "0.0.0.0",
        "--port", format("%d", var.worker_container_port),
      ]

      resources {
        limits = {
          cpu    = var.worker_cpu_staging
          memory = var.worker_memory_staging
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
        value = google_service_account.worker_staging.email
      }
      env {
        name  = "OPENAPI_ENABLED"
        value = "false"
      }
      env {
        name  = "APP_ENV"
        value = "staging"
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }
      env {
        name  = "WORKER_HTTP_DEADLINE_SECONDS"
        value = tostring(var.worker_timeout_seconds_staging)
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_project_iam_member.worker_staging_firestore_user,
  ]
}

resource "google_cloud_run_v2_service" "worker_prod" {
  name     = var.worker_service_name_prod
  location = var.region
  ingress  = var.api_ingress

  template {
    service_account = google_service_account.worker_prod.email
    timeout         = "${var.worker_timeout_seconds_prod}s"

    scaling {
      min_instance_count = 0
      max_instance_count = var.worker_max_instances_prod
    }

    containers {
      image = var.api_container_image_prod

      ports {
        container_port = var.worker_container_port
      }

      command = ["uv"]
      args = [
        "run", "uvicorn", "hsm_worker.main:app",
        "--host", "0.0.0.0",
        "--port", format("%d", var.worker_container_port),
      ]

      resources {
        limits = {
          cpu    = var.worker_cpu_prod
          memory = var.worker_memory_prod
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
        value = google_service_account.worker_prod.email
      }
      env {
        name  = "OPENAPI_ENABLED"
        value = "false"
      }
      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.firebase_project_id
      }
      env {
        name  = "WORKER_HTTP_DEADLINE_SECONDS"
        value = tostring(var.worker_timeout_seconds_prod)
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_project_iam_member.worker_prod_firestore_user,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "worker_staging_tasks_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.worker_staging.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.tasks_oidc_staging.email}"
}

resource "google_cloud_run_v2_service_iam_member" "worker_prod_tasks_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.worker_prod.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.tasks_oidc_prod.email}"
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
      env {
        name  = "USE_CLOUD_TASKS"
        value = "true"
      }
      env {
        name  = "APP_ENV"
        value = "staging"
      }
      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = var.cloud_tasks_queue_staging_id
      }
      env {
        name  = "CLOUD_TASKS_LOCATION"
        value = var.region
      }
      env {
        name  = "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT"
        value = google_service_account.tasks_oidc_staging.email
      }
      env {
        name  = "WORKER_TASK_URL"
        value = "${google_cloud_run_v2_service.worker_staging.uri}/internal/worker/run"
      }
      env {
        name  = "WORKER_HTTP_DEADLINE_SECONDS"
        value = tostring(var.worker_timeout_seconds_staging)
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
    google_cloud_run_v2_service.worker_staging,
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
        name  = "USE_CLOUD_TASKS"
        value = "true"
      }
      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = var.cloud_tasks_queue_prod_id
      }
      env {
        name  = "CLOUD_TASKS_LOCATION"
        value = var.region
      }
      env {
        name  = "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT"
        value = google_service_account.tasks_oidc_prod.email
      }
      env {
        name  = "WORKER_TASK_URL"
        value = "${google_cloud_run_v2_service.worker_prod.uri}/internal/worker/run"
      }
      env {
        name  = "WORKER_HTTP_DEADLINE_SECONDS"
        value = tostring(var.worker_timeout_seconds_prod)
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
    google_cloud_run_v2_service.worker_prod,
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
