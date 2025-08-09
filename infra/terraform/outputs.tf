output "cluster_name" {
  description = "Name of the GKE cluster"
  value       = module.gke.name
}

output "kubernetes_cluster_endpoint" {
  description = "Endpoint for the GKE master"
  value       = module.gke.endpoint
}

output "sql_instance_connection_name" {
  description = "Connection name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.connection_name
}

output "db_username" {
  description = "Database username for the application"
  value       = google_sql_user.app.name
}

output "db_password" {
  description = "Generated password for the Postgres user"
  value       = random_password.db_password.result
  sensitive   = true
}
