variable "project" {
  description = "The GCP project ID in which resources will be created"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy into"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for regional resources"
  type        = string
  default     = "us-central1-a"
}
