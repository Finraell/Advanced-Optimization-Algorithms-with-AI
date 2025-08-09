terraform {
  required_version = ">= 1.4.0"
  required_providers {
    google     = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

# Configure the Google Cloud provider. When using AWS/EKS instead of GKE
# replace this block with the aws provider and associated configuration.
provider "google" {
  project = var.project
  region  = var.region
  zone    = var.zone
}

###############################################################################
# Networking
#
# This module provisions a VPC network and one subnet. In a production setup
# you may want to customize additional subnets, IP ranges, and peerings.
###############################################################################
module "network" {
  source  = "terraform-google-modules/network/google"
  version = "~> 6.0"

  project_id   = var.project
  network_name = "aoaa-network"

  subnets = [
    {
      subnet_name   = "aoaa-subnet"
      subnet_ip     = "10.0.0.0/24"
      subnet_region = var.region
    },
  ]
}

###############################################################################
# GKE Cluster
#
# Creates a private GKE cluster with default node pool. For EKS deployments you
# would swap this module with an EKS module (e.g. terraform-aws-modules/eks/aws).
###############################################################################
module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google"
  version = "~> 27.0"

  project_id = var.project
  name       = "aoaa-gke"
  region     = var.region
  network    = module.network.network_name
  subnetwork = module.network.subnets[0].subnet_name

  ip_range_pods     = "10.2.0.0/16"
  ip_range_services = "10.3.0.0/16"

  enable_private_nodes = true
  master_authorized_networks = []
  release_channel = "REGULAR"
  node_pools = [
    {
      name               = "default-pool"
      machine_type       = "e2-standard-2"
      node_locations     = [var.zone]
      min_node_count     = 1
      max_node_count     = 3
      initial_node_count = 1
      disk_size_gb       = 100
      disk_type          = "pd-standard"
    }
  ]
}

###############################################################################
# Postgres Database
#
# Creates a Cloud SQL Postgres instance. For AWS/EKS use aws_db_instance.
###############################################################################
resource "google_sql_database_instance" "postgres" {
  name             = "aoaa-postgres"
  region           = var.region
  database_version = "POSTGRES_15"
  settings {
    tier = "db-custom-1-3840"
    availability_type = "ZONAL"
  }
}

resource "google_sql_user" "app" {
  name     = "aoaa"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}
