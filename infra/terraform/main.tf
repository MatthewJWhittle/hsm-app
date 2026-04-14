locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "firestore.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ])

  common_env = {
    GOOGLE_CLOUD_PROJECT = var.project_id
    STORAGE_BACKEND      = "gcs"
    GCS_OBJECT_PREFIX    = ""
    OPENAPI_ENABLED      = "false"
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
    timeout         = "${var.api_timeout_seconds}s"

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
