#!/bin/bash
set -e

echo "=========================================================="
echo " PHASE 1: AUTOMATED WORDPRESS & WOOCOMMERCE PROVISIONING"
echo "=========================================================="

echo "[1/6] Installing WordPress Core..."
docker exec watch_platform_wpcli wp core install \
  --url="http://localhost:8080" \
  --title="Vintage Timepiece Backend Engine" \
  --admin_user="watch_admin" \
  --admin_password="AdminPassword2026!" \
  --admin_email="admin@vintagewatchplatform.local" \
  --skip-email

echo "[2/6] Configuring Pretty Permalinks for REST API..."
docker exec watch_platform_wpcli wp option update permalink_structure '/%postname%/'
docker exec watch_platform_wpcli wp rewrite flush

echo "[3/6] Installing & Activating Core Headless Plugins..."
docker exec watch_platform_wpcli wp plugin install woocommerce --activate
docker exec watch_platform_wpcli wp plugin install cocart --activate
docker exec watch_platform_wpcli wp plugin install jwt-authentication-for-wp-rest-api --activate
docker exec watch_platform_wpcli wp plugin install advanced-custom-fields --activate

echo "[4/6] Activating Watch Headless Core Plugin..."
# Copy custom plugin into container
docker cp ./plugins/watch-headless-core watch_platform_wp:/var/www/html/wp-content/plugins/
docker exec watch_platform_wpcli wp plugin activate watch-headless-core

echo "[5/6] Configuring WooCommerce Options & HPOS..."
docker exec watch_platform_wpcli wp option update woocommerce_currency "USD"
docker exec watch_platform_wpcli wp option update woocommerce_hold_stock_minutes "60"
docker exec watch_platform_wpcli wp option update woocommerce_manage_stock "yes"
docker exec watch_platform_wpcli wp option update woocommerce_calc_taxes "no"
docker exec watch_platform_wpcli wp option update woocommerce_custom_orders_table_enabled "yes"

echo "[6/6] Generating WooCommerce REST API Consumer Keys..."
docker exec watch_platform_wpcli wp wc api_key create \
  --user_id=1 \
  --description="Storefront & Admin App Key" \
  --permissions=read_write

echo "=========================================================="
echo " SUCCESS: Backend Provisioning Complete!"
echo " URL: http://localhost:8080"
echo " REST API: http://localhost:8080/wp-json/wc/v3/products"
echo "=========================================================="
