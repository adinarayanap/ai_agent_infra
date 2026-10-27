terraform {
  backend "s3" {
    bucket       = "prompt-to-infra-tfstate-naghi20-dev"
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
