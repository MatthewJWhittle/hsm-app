output "artifact_registry_repository" {
  description = "Artifact Registry repository name."
  value       = google_artifact_registry_repository.backend.name
}

output "api_staging_uri" {
  description = "Cloud Run URI for staging API service."
  value       = google_cloud_run_v2_service.api_staging.uri
}

output "api_prod_uri" {
  description = "Cloud Run URI for production API service."
  value       = google_cloud_run_v2_service.api_prod.uri
}

output "titiler_uri" {
  description = "Cloud Run URI for shared TiTiler service."
  value       = google_cloud_run_v2_service.titiler.uri
}

output "api_staging_service_account_email" {
  description = "Runtime service account for staging API."
  value       = google_service_account.api_staging.email
}

output "api_prod_service_account_email" {
  description = "Runtime service account for production API."
  value       = google_service_account.api_prod.email
}

output "titiler_service_account_email" {
  description = "Runtime service account for TiTiler."
  value       = google_service_account.titiler.email
}

output "gcs_bucket_name" {
  description = "Model artifacts bucket name."
  value       = local.gcs_bucket_name
}
