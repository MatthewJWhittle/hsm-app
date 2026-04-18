variable "project_id" {
  description = "GCP project id (for example: hsm-dashboard)."
  type        = string
}

variable "region" {
  description = "Primary GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "artifact_registry_repository_id" {
  description = "Artifact Registry Docker repository id."
  type        = string
  default     = "hsm-app"
}

variable "titiler_service_name" {
  description = "Cloud Run service name for shared TiTiler."
  type        = string
  default     = "titiler-shared"
}

variable "titiler_container_image" {
  description = "Container image URI for TiTiler."
  type        = string
  default     = "docker.io/developmentseed/titiler:latest"
}

variable "titiler_container_port" {
  description = "Container port exposed by TiTiler."
  type        = number
  default     = 8080
}

variable "titiler_cpu" {
  description = "Cloud Run CPU limit for TiTiler container."
  type        = string
  default     = "1"
}

variable "titiler_memory" {
  description = "Cloud Run memory limit for TiTiler container."
  type        = string
  default     = "1Gi"
}

variable "titiler_min_instance_count" {
  description = "Cloud Run min instances for TiTiler (cost control: 0)."
  type        = number
  default     = 0
}

variable "titiler_max_instance_count" {
  description = "Cloud Run max instances for TiTiler."
  type        = number
  default     = 1
}

variable "titiler_ingress" {
  description = "Cloud Run ingress for TiTiler service."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "api_service_name_staging" {
  description = "Cloud Run service name for staging API."
  type        = string
  default     = "api-staging"
}

variable "api_service_name_prod" {
  description = "Cloud Run service name for production API."
  type        = string
  default     = "api-prod"
}

variable "api_container_image_staging" {
  description = "Container image URI for staging API."
  type        = string
}

variable "api_container_image_prod" {
  description = "Container image URI for production API."
  type        = string
}

variable "api_container_port" {
  description = "Container port exposed by FastAPI."
  type        = number
  default     = 8000
}

variable "api_cpu" {
  description = "Cloud Run CPU limit for API containers."
  type        = string
  default     = "1"
}

variable "api_memory" {
  description = "Cloud Run memory limit for API containers."
  type        = string
  default     = "2Gi"
}

variable "api_min_instance_count" {
  description = "Cloud Run min instances (cost control: 0)."
  type        = number
  default     = 0
}

variable "api_max_instance_count" {
  description = "Cloud Run max instances for cost control."
  type        = number
  default     = 1
}

variable "api_ingress" {
  description = "Cloud Run ingress for API services."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "api_timeout_seconds" {
  description = <<-EOT
    Maximum request duration (seconds) for api-staging and api-prod. This is a per-request ceiling: normal routes still return as fast as ever; a high value only raises how long a single stuck or long-running request may run before Cloud Run aborts it.
    When JOB_QUEUE_BACKEND is cloud_tasks or direct, POST /api/internal/jobs/run runs in-process until the job finishes — set high enough for your longest job (often 900+). With jobs disabled, 60 is usually fine.
    TiTiler uses titiler_timeout_seconds.
  EOT
  type        = number
  default     = 60
}

variable "titiler_timeout_seconds" {
  description = "Cloud Run request timeout for titiler-shared only (tile GETs; keep low)."
  type        = number
  default     = 60
}

variable "allow_unauthenticated_api" {
  description = "Whether to allow unauthenticated invocation for API services."
  type        = bool
  default     = true
}

variable "allow_unauthenticated_titiler" {
  description = "Whether to allow unauthenticated invocation for TiTiler service."
  type        = bool
  default     = true
}

variable "create_gcs_bucket" {
  description = "Whether Terraform should create the storage bucket for model artifacts."
  type        = bool
  default     = true
}

variable "gcs_bucket_name" {
  description = "GCS bucket name for model artifacts."
  type        = string
  default     = "hsm-dashboard-model-artifacts"
}

variable "gcs_bucket_location" {
  description = "Bucket location/region (use same region as compute where possible)."
  type        = string
  default     = "US-CENTRAL1"
}

variable "gcs_enable_versioning" {
  description = "Enable bucket object versioning (off by default to minimize storage cost)."
  type        = bool
  default     = false
}

variable "create_firestore_database" {
  description = "Whether Terraform should create Firestore Native database (name '(default)')."
  type        = bool
  default     = false
}

variable "create_budget_alerts" {
  description = "Create billing budget alerts for MVP cost guardrails."
  type        = bool
  default     = false
}

variable "billing_account_id" {
  description = "Billing account id for budget alerts (format: 000000-000000-000000)."
  type        = string
  default     = null
  nullable    = true
}

variable "monthly_budget_amount_usd" {
  description = "Monthly budget amount in USD for alerting."
  type        = number
  default     = 5
}

variable "budget_notification_channels" {
  description = "Optional Cloud Monitoring notification channel ids for budget alerts."
  type        = list(string)
  default     = []
}

variable "firebase_web_api_key_secret_name" {
  description = "Secret Manager secret id containing FIREBASE_WEB_API_KEY."
  type        = string
  default     = "firebase-web-api-key"
}

variable "firebase_project_id" {
  description = "Firebase project id used for token verification and Auth endpoints."
  type        = string
  default     = "hsm-dashboard"
}

variable "cors_origins_staging" {
  description = "Comma-separated CORS origins for staging API."
  type        = string
  default     = "http://localhost:5173,http://127.0.0.1:5173"
}

variable "cors_origin_regex_staging" {
  description = "Optional regex-based CORS origin allowlist for staging API."
  type        = string
  default     = ""
}

variable "cors_origins_prod" {
  description = "Comma-separated CORS origins for production API."
  type        = string
  default     = "https://hsm-dashboard.web.app,https://hsm-dashboard.firebaseapp.com"
}

variable "cors_origin_regex_prod" {
  description = "Optional regex-based CORS origin allowlist for production API."
  type        = string
  default     = ""
}

variable "cloud_tasks_queue_name" {
  description = "Cloud Tasks queue id for background jobs (e.g. environmental COG replace worker)."
  type        = string
  default     = "hsm-jobs"
}

variable "cloud_tasks_queue_location" {
  description = "Region for the Cloud Tasks queue (use the same region as Cloud Run when possible)."
  type        = string
  default     = "us-central1"
}

variable "api_staging_service_public_uri" {
  description = <<-EOT
    HTTPS origin of the staging API (no trailing slash), e.g. the value of output `api_staging_uri` after the first `terraform apply`.
    Required when `api_job_queue_backend_staging` is `cloud_tasks` or `direct` so `JOB_WORKER_URL` and OIDC audience can be set without a Terraform circular dependency on the service's own URL.
    Leave empty when job queue is `disabled` or until you copy the URL from output and apply again.
  EOT
  type        = string
  default     = ""
}

variable "api_prod_service_public_uri" {
  description = "Same as `api_staging_service_public_uri` for production (use output `api_prod_uri`)."
  type        = string
  default     = ""
}

variable "api_job_queue_backend_staging" {
  description = "Maps to Cloud Run env `JOB_QUEUE_BACKEND` for staging (`disabled`, `cloud_tasks`, or `direct`)."
  type        = string
  default     = "disabled"

  validation {
    condition     = contains(["disabled", "cloud_tasks", "direct"], var.api_job_queue_backend_staging)
    error_message = "api_job_queue_backend_staging must be disabled, cloud_tasks, or direct."
  }
}

variable "api_job_queue_backend_prod" {
  description = "Maps to Cloud Run env `JOB_QUEUE_BACKEND` for production."
  type        = string
  default     = "disabled"

  validation {
    condition     = contains(["disabled", "cloud_tasks", "direct"], var.api_job_queue_backend_prod)
    error_message = "api_job_queue_backend_prod must be disabled, cloud_tasks, or direct."
  }
}

