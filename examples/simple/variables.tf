variable "environment" {
  type = string
}

variable "logs_bucket_name" {
  type = string
}

variable "test_name" {
  type = string
}

variable "vpc_azs" {
  type = list(string)
}
