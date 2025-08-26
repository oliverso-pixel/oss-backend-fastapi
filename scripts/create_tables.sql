-- =============================================
-- 寵物社交平台資料庫架構
-- Database: oss
-- =============================================

-- 設定字符集
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET collation_connection = 'utf8mb4_unicode_ci';

-- 暫時關閉外鍵檢查
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================
-- 1. 用戶與認證相關表
-- =============================================

-- 用戶表
CREATE TABLE IF NOT EXISTS `users` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `email` VARCHAR(255) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `display_name` VARCHAR(100) DEFAULT NULL,
    `avatar_url` VARCHAR(500) DEFAULT NULL,
    `bio` TEXT DEFAULT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `is_verified` BOOLEAN DEFAULT FALSE,
    `last_login_at` TIMESTAMP NULL DEFAULT NULL,
    `last_password_change` TIMESTAMP NULL DEFAULT NULL,
    `password_reset_token` VARCHAR(255) DEFAULT NULL,
    `password_reset_expires` TIMESTAMP NULL DEFAULT NULL,
    `two_factor_enabled` BOOLEAN DEFAULT FALSE,
    `two_factor_secret` VARCHAR(255) DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_username` (`username`),
    UNIQUE KEY `idx_email` (`email`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 角色表
CREATE TABLE IF NOT EXISTS `roles` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `display_name` VARCHAR(100) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `is_system` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 權限表
CREATE TABLE IF NOT EXISTS `permissions` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `module` VARCHAR(50) NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_name` (`name`),
    KEY `idx_module_action` (`module`, `action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 角色權限關聯表
CREATE TABLE IF NOT EXISTS `role_permissions` (
    `role_id` INT UNSIGNED NOT NULL,
    `permission_id` INT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`role_id`, `permission_id`),
    CONSTRAINT `fk_role_permissions_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_role_permissions_permission` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用戶角色關聯表
CREATE TABLE IF NOT EXISTS `user_roles` (
    `user_id` BIGINT UNSIGNED NOT NULL,
    `role_id` INT UNSIGNED NOT NULL,
    `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `assigned_by` BIGINT UNSIGNED DEFAULT NULL,
    PRIMARY KEY (`user_id`, `role_id`),
    KEY `idx_role_id` (`role_id`),
    CONSTRAINT `fk_user_roles_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_roles_role` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_roles_assigner` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用戶直接權限表
CREATE TABLE IF NOT EXISTS `user_permissions` (
    `user_id` BIGINT UNSIGNED NOT NULL,
    `permission_id` INT UNSIGNED NOT NULL,
    `granted` BOOLEAN DEFAULT TRUE,
    `assigned_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `assigned_by` BIGINT UNSIGNED DEFAULT NULL,
    PRIMARY KEY (`user_id`, `permission_id`),
    CONSTRAINT `fk_user_permissions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_permissions_permission` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_permissions_assigner` FOREIGN KEY (`assigned_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- JWT Token 管理表
CREATE TABLE IF NOT EXISTS `user_tokens` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `token_type` ENUM('ACCESS', 'REFRESH') NOT NULL,
    `token_hash` VARCHAR(255) NOT NULL,
    `device_info` JSON DEFAULT NULL,
    `expires_at` TIMESTAMP NOT NULL,
    `revoked_at` TIMESTAMP NULL DEFAULT NULL,
    `last_used_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_type` (`user_id`, `token_type`),
    KEY `idx_token_hash` (`token_hash`),
    KEY `idx_expires_at` (`expires_at`),
    CONSTRAINT `fk_user_tokens_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Token 黑名單表
CREATE TABLE IF NOT EXISTS `token_blacklist` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `jti` VARCHAR(255) NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `expires_at` TIMESTAMP NOT NULL,
    `reason` VARCHAR(255) DEFAULT NULL,
    `blacklisted_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `blacklisted_by` BIGINT UNSIGNED DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_jti` (`jti`),
    KEY `idx_expires_at` (`expires_at`),
    CONSTRAINT `fk_token_blacklist_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_token_blacklist_by` FOREIGN KEY (`blacklisted_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 2. 寵物相關表
-- =============================================

-- 寵物資料表
CREATE TABLE IF NOT EXISTS `pets` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `species` ENUM('dog', 'cat', 'bird', 'rabbit', 'hamster', 'fish', 'other') NOT NULL,
    `breed` VARCHAR(100) DEFAULT NULL,
    `gender` ENUM('male', 'female', 'unknown') DEFAULT 'unknown',
    `birth_date` DATE DEFAULT NULL,
    `weight` DECIMAL(5,2) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `avatar_url` VARCHAR(500) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    CONSTRAINT `fk_pets_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 3. 貼文與媒體相關表
-- =============================================

-- 貼文表
CREATE TABLE IF NOT EXISTS `posts` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `pet_id` BIGINT UNSIGNED DEFAULT NULL,
    `content` TEXT DEFAULT NULL,
    `visibility` ENUM('public', 'friends', 'private') DEFAULT 'public',
    `location` VARCHAR(255) DEFAULT NULL,
    `latitude` DECIMAL(10, 8) DEFAULT NULL,
    `longitude` DECIMAL(11, 8) DEFAULT NULL,
    `view_count` BIGINT UNSIGNED DEFAULT 0,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_created` (`user_id`, `created_at`),
    KEY `idx_visibility_created` (`visibility`, `created_at`),
    KEY `idx_posts_timeline` (`visibility`, `created_at`, `user_id`),
    KEY `idx_posts_user_timeline` (`user_id`, `is_deleted`, `created_at`),
    CONSTRAINT `fk_posts_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_posts_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 媒體檔案表
CREATE TABLE IF NOT EXISTS `media` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `file_size` BIGINT UNSIGNED NOT NULL,
    `mime_type` VARCHAR(100) NOT NULL,
    `media_type` ENUM('image', 'video') NOT NULL,
    `width` INT UNSIGNED DEFAULT NULL,
    `height` INT UNSIGNED DEFAULT NULL,
    `duration` INT UNSIGNED DEFAULT NULL,
    `thumbnail_path` VARCHAR(500) DEFAULT NULL,
    `is_processed` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_created` (`user_id`, `created_at`),
    CONSTRAINT `fk_media_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 貼文媒體關聯表
CREATE TABLE IF NOT EXISTS `post_media` (
    `post_id` BIGINT UNSIGNED NOT NULL,
    `media_id` BIGINT UNSIGNED NOT NULL,
    `display_order` INT UNSIGNED DEFAULT 0,
    PRIMARY KEY (`post_id`, `media_id`),
    CONSTRAINT `fk_post_media_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_post_media_media` FOREIGN KEY (`media_id`) REFERENCES `media` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 相簿表
CREATE TABLE IF NOT EXISTS `albums` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `pet_id` BIGINT UNSIGNED DEFAULT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `cover_media_id` BIGINT UNSIGNED DEFAULT NULL,
    `visibility` ENUM('public', 'friends', 'private') DEFAULT 'private',
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_created` (`user_id`, `created_at`),
    CONSTRAINT `fk_albums_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_albums_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_albums_cover` FOREIGN KEY (`cover_media_id`) REFERENCES `media` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 相簿媒體關聯表
CREATE TABLE IF NOT EXISTS `album_media` (
    `album_id` BIGINT UNSIGNED NOT NULL,
    `media_id` BIGINT UNSIGNED NOT NULL,
    `display_order` INT UNSIGNED DEFAULT 0,
    `added_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`album_id`, `media_id`),
    CONSTRAINT `fk_album_media_album` FOREIGN KEY (`album_id`) REFERENCES `albums` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_album_media_media` FOREIGN KEY (`media_id`) REFERENCES `media` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 4. 社交功能相關表
-- =============================================

-- 標籤表
CREATE TABLE IF NOT EXISTS `tags` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `usage_count` BIGINT UNSIGNED DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_name` (`name`),
    KEY `idx_usage_count` (`usage_count`),
    KEY `idx_tags_search` (`name`, `usage_count`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 貼文標籤關聯表
CREATE TABLE IF NOT EXISTS `post_tags` (
    `post_id` BIGINT UNSIGNED NOT NULL,
    `tag_id` BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (`post_id`, `tag_id`),
    CONSTRAINT `fk_post_tags_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_post_tags_tag` FOREIGN KEY (`tag_id`) REFERENCES `tags` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 好友關係表
CREATE TABLE IF NOT EXISTS `friendships` (
    `user_id` BIGINT UNSIGNED NOT NULL,
    `friend_id` BIGINT UNSIGNED NOT NULL,
    `status` ENUM('pending', 'accepted', 'blocked') DEFAULT 'pending',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `accepted_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`user_id`, `friend_id`),
    KEY `idx_friend_status` (`friend_id`, `status`),
    CONSTRAINT `fk_friendships_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_friendships_friend` FOREIGN KEY (`friend_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 關注關係表
CREATE TABLE IF NOT EXISTS `follows` (
    `follower_id` BIGINT UNSIGNED NOT NULL,
    `following_id` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`follower_id`, `following_id`),
    KEY `idx_following_created` (`following_id`, `created_at`),
    CONSTRAINT `fk_follows_follower` FOREIGN KEY (`follower_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_follows_following` FOREIGN KEY (`following_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 按讚表
CREATE TABLE IF NOT EXISTS `likes` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `post_id` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_user_post` (`user_id`, `post_id`),
    KEY `idx_post_created` (`post_id`, `created_at`),
    CONSTRAINT `fk_likes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_likes_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 評論表
CREATE TABLE IF NOT EXISTS `comments` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `post_id` BIGINT UNSIGNED NOT NULL,
    `parent_id` BIGINT UNSIGNED DEFAULT NULL,
    `content` TEXT NOT NULL,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_post_created` (`post_id`, `created_at`),
    CONSTRAINT `fk_comments_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_parent` FOREIGN KEY (`parent_id`) REFERENCES `comments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 5. 商戶與商品相關表
-- =============================================

-- 商戶表
CREATE TABLE IF NOT EXISTS `merchants` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `shop_name` VARCHAR(200) NOT NULL,
    `shop_slug` VARCHAR(100) NOT NULL,
    `business_type` ENUM('individual', 'company') NOT NULL,
    `business_registration_no` VARCHAR(100) DEFAULT NULL,
    `tax_id` VARCHAR(50) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `logo_url` VARCHAR(500) DEFAULT NULL,
    `banner_url` VARCHAR(500) DEFAULT NULL,
    `contact_email` VARCHAR(255) DEFAULT NULL,
    `contact_phone` VARCHAR(20) DEFAULT NULL,
    `business_hours` JSON DEFAULT NULL,
    `address` JSON DEFAULT NULL,
    `bank_account` JSON DEFAULT NULL,
    `commission_rate` DECIMAL(5,2) DEFAULT 10.00,
    `status` ENUM('pending', 'approved', 'suspended', 'rejected') DEFAULT 'pending',
    `verified_at` TIMESTAMP NULL DEFAULT NULL,
    `verified_by` BIGINT UNSIGNED DEFAULT NULL,
    `rejection_reason` TEXT DEFAULT NULL,
    `rating` DECIMAL(3,2) DEFAULT 0.00,
    `total_sales` BIGINT UNSIGNED DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_user_id` (`user_id`),
    UNIQUE KEY `idx_shop_slug` (`shop_slug`),
    KEY `idx_status` (`status`),
    KEY `idx_rating` (`rating`),
    CONSTRAINT `fk_merchants_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_merchants_verifier` FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 商戶文件表
CREATE TABLE IF NOT EXISTS `merchant_documents` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `merchant_id` BIGINT UNSIGNED NOT NULL,
    `document_type` ENUM('business_license', 'tax_certificate', 'id_card', 'bank_statement', 'other') NOT NULL,
    `file_path` VARCHAR(500) NOT NULL,
    `file_name` VARCHAR(255) NOT NULL,
    `status` ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    `verified_at` TIMESTAMP NULL DEFAULT NULL,
    `verified_by` BIGINT UNSIGNED DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_merchant_type` (`merchant_id`, `document_type`),
    CONSTRAINT `fk_merchant_documents_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_merchant_documents_verifier` FOREIGN KEY (`verified_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 訂單表（需要先創建，因為 merchant_reviews 依賴它）
CREATE TABLE IF NOT EXISTS `orders` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `order_number` VARCHAR(50) NOT NULL,
    `status` ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') DEFAULT 'pending',
    `subtotal` DECIMAL(10,2) NOT NULL,
    `shipping_fee` DECIMAL(10,2) DEFAULT 0.00,
    `tax` DECIMAL(10,2) DEFAULT 0.00,
    `total` DECIMAL(10,2) NOT NULL,
    `payment_method` VARCHAR(50) DEFAULT NULL,
    `payment_status` ENUM('pending', 'paid', 'failed', 'refunded') DEFAULT 'pending',
    `shipping_address` JSON DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_order_number` (`order_number`),
    KEY `idx_user_created` (`user_id`, `created_at`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 商戶評價表
CREATE TABLE IF NOT EXISTS `merchant_reviews` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `merchant_id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `order_id` BIGINT UNSIGNED NOT NULL,
    `rating` TINYINT UNSIGNED NOT NULL CHECK (`rating` >= 1 AND `rating` <= 5),
    `comment` TEXT DEFAULT NULL,
    `is_anonymous` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_user_order` (`user_id`, `order_id`),
    KEY `idx_merchant_rating` (`merchant_id`, `rating`),
    CONSTRAINT `fk_merchant_reviews_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_merchant_reviews_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_merchant_reviews_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 商品分類表
CREATE TABLE IF NOT EXISTS `product_categories` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `slug` VARCHAR(100) NOT NULL,
    `parent_id` INT UNSIGNED DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `display_order` INT UNSIGNED DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_slug` (`slug`),
    KEY `idx_parent_active` (`parent_id`, `is_active`),
    CONSTRAINT `fk_product_categories_parent` FOREIGN KEY (`parent_id`) REFERENCES `product_categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 商品表
CREATE TABLE IF NOT EXISTS `products` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `category_id` INT UNSIGNED NOT NULL,
    `merchant_id` BIGINT UNSIGNED NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `price` DECIMAL(10,2) NOT NULL,
    `sale_price` DECIMAL(10,2) DEFAULT NULL,
    `stock_quantity` INT UNSIGNED DEFAULT 0,
    `sku` VARCHAR(100) DEFAULT NULL,
    `status` ENUM('active', 'inactive', 'out_of_stock') DEFAULT 'active',
    `view_count` BIGINT UNSIGNED DEFAULT 0,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_sku` (`sku`),
    KEY `idx_category_status` (`category_id`, `status`),
    KEY `idx_merchant_status` (`merchant_id`, `status`),
    KEY `idx_products_search` (`status`, `category_id`, `created_at`),
    FULLTEXT KEY `idx_products_fulltext` (`name`, `description`),
    CONSTRAINT `fk_products_category` FOREIGN KEY (`category_id`) REFERENCES `product_categories` (`id`),
    CONSTRAINT `fk_products_merchant` FOREIGN KEY (`merchant_id`) REFERENCES `merchants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 商品媒體關聯表
CREATE TABLE IF NOT EXISTS `product_media` (
    `product_id` BIGINT UNSIGNED NOT NULL,
    `media_id` BIGINT UNSIGNED NOT NULL,
    `is_primary` BOOLEAN DEFAULT FALSE,
    `display_order` INT UNSIGNED DEFAULT 0,
    PRIMARY KEY (`product_id`, `media_id`),
    CONSTRAINT `fk_product_media_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_product_media_media` FOREIGN KEY (`media_id`) REFERENCES `media` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 訂單項目表
CREATE TABLE IF NOT EXISTS `order_items` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `order_id` BIGINT UNSIGNED NOT NULL,
    `product_id` BIGINT UNSIGNED NOT NULL,
    `quantity` INT UNSIGNED NOT NULL,
    `price` DECIMAL(10,2) NOT NULL,
    `total` DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_order_id` (`order_id`),
    CONSTRAINT `fk_order_items_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_order_items_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 7. 寵物醫療相關表
-- =============================================

-- 獸醫診所表
CREATE TABLE IF NOT EXISTS `veterinary_clinics` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(200) NOT NULL,
    `license_no` VARCHAR(100) DEFAULT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `email` VARCHAR(255) DEFAULT NULL,
    `address` JSON DEFAULT NULL,
    `latitude` DECIMAL(10, 8) DEFAULT NULL,
    `longitude` DECIMAL(11, 8) DEFAULT NULL,
    `is_verified` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_location` (`latitude`, `longitude`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 獸醫師表
CREATE TABLE IF NOT EXISTS `veterinarians` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `clinic_id` BIGINT UNSIGNED DEFAULT NULL,
    `name` VARCHAR(100) NOT NULL,
    `license_no` VARCHAR(100) DEFAULT NULL,
    `specialization` VARCHAR(200) DEFAULT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `email` VARCHAR(255) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_license` (`license_no`),
    CONSTRAINT `fk_veterinarians_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 疫苗類型表
CREATE TABLE IF NOT EXISTS `vaccine_types` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `species` ENUM('dog', 'cat', 'rabbit', 'other') NOT NULL,
    `name` VARCHAR(100) NOT NULL,
    `abbreviation` VARCHAR(20) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `recommended_age_weeks` INT UNSIGNED DEFAULT NULL,
    `booster_interval_months` INT UNSIGNED DEFAULT NULL,
    `is_core` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_species` (`species`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 寵物病歷表
CREATE TABLE IF NOT EXISTS `pet_medical_records` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `pet_id` BIGINT UNSIGNED NOT NULL,
    `clinic_id` BIGINT UNSIGNED DEFAULT NULL,
    `veterinarian_id` BIGINT UNSIGNED DEFAULT NULL,
    `visit_date` DATE NOT NULL,
    `visit_type` ENUM('routine_checkup', 'vaccination', 'illness', 'injury', 'surgery', 'emergency', 'other') NOT NULL,
    `chief_complaint` TEXT DEFAULT NULL,
    `symptoms` TEXT DEFAULT NULL,
    `diagnosis` TEXT DEFAULT NULL,
    `treatment` TEXT DEFAULT NULL,
    `prescription` JSON DEFAULT NULL,
    `weight` DECIMAL(5,2) DEFAULT NULL,
    `temperature` DECIMAL(4,1) DEFAULT NULL,
    `heart_rate` INT UNSIGNED DEFAULT NULL,
    `respiratory_rate` INT UNSIGNED DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `follow_up_date` DATE DEFAULT NULL,
    `attachments` JSON DEFAULT NULL,
    `created_by` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_pet_date` (`pet_id`, `visit_date` DESC),
    KEY `idx_visit_type` (`visit_type`),
    CONSTRAINT `fk_pet_medical_records_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pet_medical_records_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_pet_medical_records_vet` FOREIGN KEY (`veterinarian_id`) REFERENCES `veterinarians` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_pet_medical_records_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 寵物疫苗接種記錄表
CREATE TABLE IF NOT EXISTS `pet_vaccinations` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `pet_id` BIGINT UNSIGNED NOT NULL,
    `vaccine_type_id` INT UNSIGNED NOT NULL,
    `medical_record_id` BIGINT UNSIGNED DEFAULT NULL,
    `vaccination_date` DATE NOT NULL,
    `batch_number` VARCHAR(100) DEFAULT NULL,
    `manufacturer` VARCHAR(100) DEFAULT NULL,
    `clinic_id` BIGINT UNSIGNED DEFAULT NULL,
    `veterinarian_id` BIGINT UNSIGNED DEFAULT NULL,
    `next_due_date` DATE DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `certificate_no` VARCHAR(100) DEFAULT NULL,
    `created_by` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_pet_date` (`pet_id`, `vaccination_date` DESC),
    KEY `idx_due_date` (`next_due_date`),
    CONSTRAINT `fk_pet_vaccinations_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pet_vaccinations_vaccine` FOREIGN KEY (`vaccine_type_id`) REFERENCES `vaccine_types` (`id`),
    CONSTRAINT `fk_pet_vaccinations_record` FOREIGN KEY (`medical_record_id`) REFERENCES `pet_medical_records` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_pet_vaccinations_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_pet_vaccinations_vet` FOREIGN KEY (`veterinarian_id`) REFERENCES `veterinarians` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_pet_vaccinations_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 寵物用藥記錄表
CREATE TABLE IF NOT EXISTS `pet_medications` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `pet_id` BIGINT UNSIGNED NOT NULL,
    `medical_record_id` BIGINT UNSIGNED DEFAULT NULL,
    `medication_name` VARCHAR(200) NOT NULL,
    `medication_type` ENUM('oral', 'injection', 'topical', 'other') NOT NULL,
    `dosage` VARCHAR(100) DEFAULT NULL,
    `frequency` VARCHAR(100) DEFAULT NULL,
    `start_date` DATE NOT NULL,
    `end_date` DATE DEFAULT NULL,
    `purpose` TEXT DEFAULT NULL,
    `side_effects` TEXT DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_by` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_pet_dates` (`pet_id`, `start_date`, `end_date`),
    CONSTRAINT `fk_pet_medications_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pet_medications_record` FOREIGN KEY (`medical_record_id`) REFERENCES `pet_medical_records` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_pet_medications_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 寵物健康提醒表
CREATE TABLE IF NOT EXISTS `pet_health_reminders` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `pet_id` BIGINT UNSIGNED NOT NULL,
    `reminder_type` ENUM('vaccination', 'checkup', 'medication', 'grooming', 'other') NOT NULL,
    `title` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `due_date` DATE NOT NULL,
    `reminder_date` DATE NOT NULL,
    `is_completed` BOOLEAN DEFAULT FALSE,
    `completed_at` TIMESTAMP NULL DEFAULT NULL,
    `created_by` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_pet_reminder` (`pet_id`, `reminder_date`),
    KEY `idx_due_date` (`due_date`, `is_completed`),
    CONSTRAINT `fk_pet_health_reminders_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pet_health_reminders_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- 8. 其他功能表
-- =============================================

-- 通知表
CREATE TABLE IF NOT EXISTS `notifications` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `type` VARCHAR(50) NOT NULL,
    `title` VARCHAR(200) DEFAULT NULL,
    `content` TEXT DEFAULT NULL,
    `data` JSON DEFAULT NULL,
    `is_read` BOOLEAN DEFAULT FALSE,
    `read_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_read_created` (`user_id`, `is_read`, `created_at`),
    KEY `idx_notifications_unread` (`user_id`, `is_read`, `created_at`),
    CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 聊天室表
CREATE TABLE IF NOT EXISTS `chat_rooms` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `type` ENUM('private', 'group') DEFAULT 'private',
    `name` VARCHAR(100) DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 聊天室成員表
CREATE TABLE IF NOT EXISTS `chat_room_members` (
    `room_id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `role` ENUM('member', 'admin') DEFAULT 'member',
    `joined_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `last_read_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`room_id`, `user_id`),
    KEY `idx_user_joined` (`user_id`, `joined_at`),
    CONSTRAINT `fk_chat_room_members_room` FOREIGN KEY (`room_id`) REFERENCES `chat_rooms` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_chat_room_members_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 聊天訊息表
CREATE TABLE IF NOT EXISTS `chat_messages` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `room_id` BIGINT UNSIGNED NOT NULL,
    `sender_id` BIGINT UNSIGNED NOT NULL,
    `message` TEXT NOT NULL,
    `media_id` BIGINT UNSIGNED DEFAULT NULL,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_room_created` (`room_id`, `created_at`),
    CONSTRAINT `fk_chat_messages_room` FOREIGN KEY (`room_id`) REFERENCES `chat_rooms` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_chat_messages_sender` FOREIGN KEY (`sender_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_chat_messages_media` FOREIGN KEY (`media_id`) REFERENCES `media` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 審計日誌表
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `username` VARCHAR(50) NOT NULL,
    `action` VARCHAR(100) NOT NULL,
    `resource_type` VARCHAR(50) DEFAULT NULL,
    `resource_id` BIGINT UNSIGNED DEFAULT NULL,
    `details` JSON DEFAULT NULL,
    `ip_address` VARCHAR(45) DEFAULT NULL,
    `user_agent` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_action` (`action`),
    KEY `idx_resource` (`resource_type`, `resource_id`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 重新開啟外鍵檢查
SET FOREIGN_KEY_CHECKS = 1;

-- -- =============================================
-- -- 9. 插入初始數據
-- -- =============================================

-- -- 插入預設角色
-- INSERT INTO `roles` (`name`, `display_name`, `description`, `is_system`) VALUES
-- ('super_admin', '超級管理員', '擁有所有權限', TRUE),
-- ('admin', '管理員', '一般管理權限', TRUE),
-- ('merchant', '商戶', '可以販售商品', TRUE),
-- ('user', '一般用戶', '基本用戶權限', TRUE),
-- ('guest', '訪客', '僅可瀏覽公開內容', TRUE)
-- ON DUPLICATE KEY UPDATE `display_name` = VALUES(`display_name`);

-- -- 插入基本權限
-- INSERT INTO `permissions` (`module`, `action`, `name`, `description`) VALUES
-- -- 用戶模組
-- ('user', 'create', 'user.create', '建立用戶'),
-- ('user', 'read', 'user.read', '查看用戶'),
-- ('user', 'update', 'user.update', '更新用戶'),
-- ('user', 'delete', 'user.delete', '刪除用戶'),
-- ('user', 'manage', 'user.manage', '管理所有用戶'),
-- -- 貼文模組
-- ('post', 'create', 'post.create', '建立貼文'),
-- ('post', 'read', 'post.read', '查看貼文'),
-- ('post', 'update', 'post.update', '更新自己的貼文'),
-- ('post', 'delete', 'post.delete', '刪除自己的貼文'),
-- ('post', 'manage', 'post.manage', '管理所有貼文'),
-- -- 商品模組
-- ('product', 'create', 'product.create', '建立商品'),
-- ('product', 'read', 'product.read', '查看商品'),
-- ('product', 'update', 'product.update', '更新商品'),
-- ('product', 'delete', 'product.delete', '刪除商品'),
-- ('product', 'manage', 'product.manage', '管理所有商品'),
-- -- 商戶模組
-- ('merchant', 'apply', 'merchant.apply', '申請成為商戶'),
-- ('merchant', 'manage', 'merchant.manage', '管理商戶'),
-- -- 醫療記錄模組
-- ('medical', 'create', 'medical.create', '建立醫療記錄'),
-- ('medical', 'read', 'medical.read', '查看自己寵物的醫療記錄'),
-- ('medical', 'update', 'medical.update', '更新醫療記錄'),
-- ('medical', 'delete', 'medical.delete', '刪除醫療記錄'),
-- ('medical', 'manage', 'medical.manage', '管理所有醫療記錄'),
-- -- 管理模組
-- ('admin', 'access', 'admin.access', '訪問管理後台'),
-- ('admin', 'manage', 'admin.manage', '所有管理權限')
-- ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

-- -- 插入常見疫苗類型
-- INSERT INTO `vaccine_types` (`species`, `name`, `abbreviation`, `description`, `recommended_age_weeks`, `booster_interval_months`, `is_core`) VALUES
-- -- 狗疫苗
-- ('dog', '犬瘟熱疫苗', 'CDV', '預防犬瘟熱病毒', 6, 12, TRUE),
-- ('dog', '犬小病毒疫苗', 'CPV', '預防犬小病毒感染', 6, 12, TRUE),
-- ('dog', '犬傳染性肝炎疫苗', 'CAV', '預防犬傳染性肝炎', 6, 12, TRUE),
-- ('dog', '狂犬病疫苗', 'Rabies', '預防狂犬病', 12, 12, TRUE),
-- ('dog', '犬舍咳疫苗', 'KC', '預防犬舍咳', 8, 12, FALSE),
-- -- 貓疫苗
-- ('cat', '貓瘟疫苗', 'FPV', '預防貓瘟', 8, 12, TRUE),
-- ('cat', '貓鼻氣管炎疫苗', 'FHV', '預防貓鼻氣管炎', 8, 12, TRUE),
-- ('cat', '貓杯狀病毒疫苗', 'FCV', '預防貓杯狀病毒', 8, 12, TRUE),
-- ('cat', '狂犬病疫苗', 'Rabies', '預防狂犬病', 12, 12, TRUE),
-- ('cat', '貓白血病疫苗', 'FeLV', '預防貓白血病', 8, 12, FALSE)
-- ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

-- -- 設定角色權限關聯（示例）
-- -- 超級管理員擁有所有權限
-- INSERT INTO `role_permissions` (`role_id`, `permission_id`)
-- SELECT 1, `id` FROM `permissions`
-- ON DUPLICATE KEY UPDATE `role_id` = VALUES(`role_id`);

-- -- 一般用戶的基本權限
-- INSERT INTO `role_permissions` (`role_id`, `permission_id`)
-- SELECT 4, `id` FROM `permissions` 
-- WHERE `name` IN ('user.read', 'user.update', 'post.create', 'post.read', 'post.update', 'post.delete', 'product.read', 'medical.create', 'medical.read')
-- ON DUPLICATE KEY UPDATE `role_id` = VALUES(`role_id`);

-- -- 商戶權限
-- INSERT INTO `role_permissions` (`role_id`, `permission_id`)
-- SELECT 3, `id` FROM `permissions` 
-- WHERE `name` IN ('user.read', 'user.update', 'post.create', 'post.read', 'post.update', 'post.delete', 'product.create', 'product.read', 'product.update', 'product.delete', 'merchant.apply', 'medical.create', 'medical.read')
-- ON DUPLICATE KEY UPDATE `role_id` = VALUES(`role_id`);