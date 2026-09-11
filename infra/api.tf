resource "aws_cognito_user_pool" "analysts" {

  name                     = "${local.name}-analysts"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 1

  }
  mfa_configuration = "ON"
  software_token_mfa_configuration {
    enabled = true
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1

    }

  }

}
resource "aws_cognito_resource_server" "api" {

  identifier   = "threatlens"
  name         = "ThreatLens API"
  user_pool_id = aws_cognito_user_pool.analysts.id
  scope {
    scope_name        = "read"
    scope_description = "Read shared SOC incidents"

  }
  scope {
    scope_name        = "write"
    scope_description = "Update shared SOC incident investigations"

  }

}
resource "aws_cognito_user_pool_domain" "analysts" {

  domain       = "${local.name}-${local.suffix}"
  user_pool_id = aws_cognito_user_pool.analysts.id

}
resource "aws_cognito_user_pool_client" "web" {

  name                                 = "${local.name}-web"
  user_pool_id                         = aws_cognito_user_pool.analysts.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "threatlens/read", "threatlens/write"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = ["${local.frontend_origin}/"]
  logout_urls                          = ["${local.frontend_origin}/"]
  access_token_validity                = 15
  id_token_validity                    = 15
  token_validity_units {
    access_token = "minutes"
    id_token     = "minutes"

  }
  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
  depends_on                    = [aws_cognito_resource_server.api]

}
resource "aws_apigatewayv2_api" "api" {

  name          = "${local.name}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = [local.frontend_origin]
    allow_methods = ["GET", "PATCH", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
    max_age       = 300

  }

}
resource "aws_apigatewayv2_authorizer" "cognito" {

  api_id           = aws_apigatewayv2_api.api.id
  name             = "analysts"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.web.id]
    issuer   = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.analysts.id}"

  }

}
resource "aws_apigatewayv2_integration" "api" {

  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app["api"].invoke_arn
  payload_format_version = "2.0"

}
resource "aws_apigatewayv2_route" "api" {

  for_each = {
    "GET /incidents" = "threatlens/read", "GET /incidents/{id}" = "threatlens/read", "PATCH /incidents/{id}" = "threatlens/write"
  }
  api_id               = aws_apigatewayv2_api.api.id
  route_key            = each.key
  target               = "integrations/${aws_apigatewayv2_integration.api.id}"
  authorization_type   = "JWT"
  authorizer_id        = aws_apigatewayv2_authorizer.cognito.id
  authorization_scopes = [each.value]

}
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${local.name}"
  retention_in_days = 14

}
resource "aws_apigatewayv2_stage" "default" {

  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit   = 10
    throttling_rate_limit    = 5
    detailed_metrics_enabled = true

  }
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId = "$context.requestId", route = "$context.routeKey", status = "$context.status", responseLength = "$context.responseLength", integrationError = "$context.integrationErrorMessage"
    })

  }

}
resource "aws_lambda_permission" "api" {

  statement_id  = "AllowHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app["api"].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"

}
