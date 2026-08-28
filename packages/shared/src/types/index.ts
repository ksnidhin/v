/**
 * @watch-platform/shared — Core TypeScript Data Models
 * Master Source of Truth for Storefront App & Admin Dashboard App
 */

export type ConditionGrade = 
  | 'Mint' 
  | 'Near Mint' 
  | 'Excellent' 
  | 'Very Good' 
  | 'Good' 
  | 'Fair';

export type MovementType = 'Manual Winding' | 'Automatic' | 'Quartz' | 'Tuning Fork';

export interface WatchSpecs {
  reference_number: string;
  movement_type: MovementType;
  caliber: string;
  serial_number: string;
  year_of_production: number;
  case_material: string;
  case_diameter_mm: number;
  lug_width_mm: number;
  dial_color: string;
  crystal_type: string;
  box_included: boolean;
  papers_included: boolean;
  condition_grade: ConditionGrade;
  service_history: string;
}

export interface ProductImage {
  id: number;
  src: string;
  alt: string;
  srcset?: string;
  width: number;
  height: number;
  blurDataURL?: string;
}

export type ProductStatus = 'publish' | 'draft' | 'private' | 'trash';
export type StockStatus = 'instock' | 'outofstock' | 'onbackorder';

export interface VintageWatchProduct {
  id: number;
  name: string;
  slug: string;
  permalink: string;
  status: ProductStatus;
  featured: boolean;
  sku: string;
  price: string;
  regular_price: string;
  sale_price: string;
  on_sale: boolean;
  purchasable: boolean;
  stock_quantity: number;
  stock_status: StockStatus;
  sold_individually: boolean;
  images: ProductImage[];
  categories: Array<{ id: number; name: string; slug: string }>;
  tags: Array<{ id: number; name: string; slug: string }>;
  acf_specs: WatchSpecs;
  created_at: string;
  updated_at: string;
}

export type OrderStatus = 
  | 'pending' 
  | 'processing' 
  | 'on-hold' 
  | 'completed' 
  | 'cancelled' 
  | 'refunded' 
  | 'failed';

export interface OrderLineItem {
  id: number;
  name: string;
  product_id: number;
  quantity: number;
  subtotal: string;
  total: string;
  sku: string;
  price: number;
}

export interface Order {
  id: number;
  status: OrderStatus;
  currency: string;
  total: string;
  customer_id: number;
  billing: {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    address_1: string;
    city: string;
    postcode: string;
    country: string;
  };
  shipping: {
    first_name: string;
    last_name: string;
    address_1: string;
    city: string;
    postcode: string;
    country: string;
  };
  line_items: OrderLineItem[];
  date_created: string;
  transaction_id: string;
}
