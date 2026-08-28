<?php
/**
 * Plugin Name: Watch Headless Core
 * Description: Registers ACF watch specifications, exposes REST fields, and configures CORS for Next.js storefront & Refine admin app.
 * Version: 1.0.0
 * Author: Vintage Watch Platform Engine
 */

if (!defined('ABSPATH')) {
    exit;
}

// 1. Enable CORS for local Next.js storefront (3000) & Refine admin (3001)
add_action('rest_api_init', function () {
    remove_filter('rest_pre_serve_request', 'rest_send_cors_headers');
    add_filter('rest_pre_serve_request', function ($value) {
        $origin = get_http_origin();
        $allowed_origins = [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001'
        ];

        if (in_array($origin, $allowed_origins, true)) {
            header('Access-Control-Allow-Origin: ' . esc_url_raw($origin));
            header('Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS');
            header('Access-Control-Allow-Credentials: true');
            header('Access-Control-Allow-Headers: Authorization, X-WP-Nonce, Content-Type, Cart-Token');
        }
        return $value;
    });
}, 15);

// 2. Register ACF Custom Fields Programmatically for Products
add_action('acf/init', function () {
    if (function_exists('acf_add_local_field_group')) {
        acf_add_local_field_group([
            'key' => 'group_watch_specifications',
            'title' => 'Watch Technical Specifications',
            'fields' => [
                ['key' => 'field_ref_num', 'label' => 'Reference Number', 'name' => 'reference_number', 'type' => 'text', 'required' => 1],
                ['key' => 'field_mov_type', 'label' => 'Movement Type', 'name' => 'movement_type', 'type' => 'select', 'choices' => ['Manual Winding' => 'Manual Winding', 'Automatic' => 'Automatic', 'Quartz' => 'Quartz', 'Tuning Fork' => 'Tuning Fork']],
                ['key' => 'field_caliber', 'label' => 'Caliber', 'name' => 'caliber', 'type' => 'text', 'required' => 1],
                ['key' => 'field_serial_num', 'label' => 'Serial Number', 'name' => 'serial_number', 'type' => 'text'],
                ['key' => 'field_prod_year', 'label' => 'Year of Production', 'name' => 'year_of_production', 'type' => 'number'],
                ['key' => 'field_case_mat', 'label' => 'Case Material', 'name' => 'case_material', 'type' => 'text'],
                ['key' => 'field_case_diam', 'label' => 'Case Diameter (mm)', 'name' => 'case_diameter_mm', 'type' => 'number'],
                ['key' => 'field_lug_width', 'label' => 'Lug Width (mm)', 'name' => 'lug_width_mm', 'type' => 'number'],
                ['key' => 'field_dial_color', 'label' => 'Dial Color', 'name' => 'dial_color', 'type' => 'text'],
                ['key' => 'field_crystal', 'label' => 'Crystal Type', 'name' => 'crystal_type', 'type' => 'text'],
                ['key' => 'field_box_inc', 'label' => 'Box Included', 'name' => 'box_included', 'type' => 'true_false'],
                ['key' => 'field_papers_inc', 'label' => 'Papers Included', 'name' => 'papers_included', 'type' => 'true_false'],
                ['key' => 'field_cond_grade', 'label' => 'Condition Grade', 'name' => 'condition_grade', 'type' => 'select', 'choices' => ['Mint' => 'Mint', 'Near Mint' => 'Near Mint', 'Excellent' => 'Excellent', 'Very Good' => 'Very Good', 'Good' => 'Good', 'Fair' => 'Fair']],
                ['key' => 'field_serv_hist', 'label' => 'Service History', 'name' => 'service_history', 'type' => 'textarea'],
            ],
            'location' => [
                [['param' => 'post_type', 'operator' => '==', 'value' => 'product']]
            ],
        ]);
    }
});

// 3. Expose acf_specs in WooCommerce REST API Product Responses
add_action('rest_api_init', function () {
    register_rest_field('product', 'acf_specs', [
        'get' => function ($object) {
            $product_id = $object['id'];
            return [
                'reference_number' => get_field('reference_number', $product_id) ?: '',
                'movement_type' => get_field('movement_type', $product_id) ?: 'Manual Winding',
                'caliber' => get_field('caliber', $product_id) ?: '',
                'serial_number' => get_field('serial_number', $product_id) ?: '',
                'year_of_production' => (int) get_field('year_of_production', $product_id) ?: 1970,
                'case_material' => get_field('case_material', $product_id) ?: 'Stainless Steel',
                'case_diameter_mm' => (float) get_field('case_diameter_mm', $product_id) ?: 40,
                'lug_width_mm' => (float) get_field('lug_width_mm', $product_id) ?: 20,
                'dial_color' => get_field('dial_color', $product_id) ?: 'Black',
                'crystal_type' => get_field('crystal_type', $product_id) ?: 'Hesalite',
                'box_included' => (bool) get_field('box_included', $product_id),
                'papers_included' => (bool) get_field('papers_included', $product_id),
                'condition_grade' => get_field('condition_grade', $product_id) ?: 'Excellent',
                'service_history' => get_field('service_history', $product_id) ?: 'Fully serviced in-house.',
            ];
        },
        'schema' => null,
    ]);
});
