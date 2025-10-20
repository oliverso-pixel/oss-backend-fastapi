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
    `background_image_url` VARCHAR(500) DEFAULT NULL,
    `bio` TEXT DEFAULT NULL,
    `birth_date` TIMESTAMP NULL DEFAULT NULL,
    `location_latitude` DECIMAL(10, 8) DEFAULT NULL,
    `location_longitude` DECIMAL(11, 8) DEFAULT NULL,
    `location_address` VARCHAR(500) DEFAULT NULL,
    `location_city` VARCHAR(100) DEFAULT NULL,
    `location_country` VARCHAR(100) DEFAULT NULL,
    `location_updated_at` TIMESTAMP NULL DEFAULT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `is_verified` BOOLEAN DEFAULT FALSE,
    `last_login_at` TIMESTAMP NULL DEFAULT NULL,
    `last_password_change` TIMESTAMP NULL DEFAULT NULL,
    `password_reset_token` VARCHAR(255) DEFAULT NULL,
    `password_reset_expires` TIMESTAMP NULL DEFAULT NULL,
    `two_factor_enabled` BOOLEAN DEFAULT FALSE,
    `two_factor_secret` VARCHAR(255) DEFAULT NULL,
    `privacy_level` ENUM('public', 'private') DEFAULT 'public',
    `show_email` BOOLEAN DEFAULT FALSE,
    `show_phone` BOOLEAN DEFAULT FALSE,
    `show_online_status` BOOLEAN DEFAULT TRUE,
    `show_last_seen` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_username` (`username`),
    UNIQUE KEY `idx_email` (`email`),
    KEY `idx_users_privacy_level` (`privacy_level`),
    KEY `idx_created_at` (`created_at`),
    KEY `idx_location` (`location_latitude`, `location_longitude`),
    KEY `idx_location_city_country` (`location_city`, `location_country`)
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
    `jti` VARCHAR(255) DEFAULT NULL,
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
    KEY `idx_jti` (`jti`),
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
    `privacy_level` ENUM('public', 'private') DEFAULT 'public',
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_privacy_level` (`privacy_level`),
    KEY `idx_pets_privacy_user` (`user_id`, `privacy_level`, `is_active`),
    CONSTRAINT `fk_pets_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 寵物轉移記錄表
CREATE TABLE IF NOT EXISTS `pet_transfer_history` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `pet_id` BIGINT UNSIGNED NOT NULL,
    `from_user_id` BIGINT UNSIGNED NOT NULL,
    `to_user_id` BIGINT UNSIGNED NOT NULL,
    `transfer_reason` TEXT DEFAULT NULL,
    `transfer_type` ENUM('gift', 'sale', 'adoption', 'other') DEFAULT 'other',
    `transfer_fee` DECIMAL(10,2) DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `status` ENUM('pending', 'accepted', 'rejected', 'cancelled') DEFAULT 'pending',
    `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `responded_at` TIMESTAMP NULL DEFAULT NULL,
    `completed_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_pet_id` (`pet_id`),
    KEY `idx_from_user` (`from_user_id`),
    KEY `idx_to_user` (`to_user_id`),
    KEY `idx_status` (`status`),
    CONSTRAINT `fk_pet_transfer_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pet_transfer_from` FOREIGN KEY (`from_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pet_transfer_to` FOREIGN KEY (`to_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
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
    `visibility` ENUM('PUBLIC', 'FRIENDS', 'PRIVATE') DEFAULT 'PUBLIC',
    `location` VARCHAR(255) DEFAULT NULL,
    `latitude` DECIMAL(10, 8) DEFAULT NULL,
    `longitude` DECIMAL(11, 8) DEFAULT NULL,
    `view_count` BIGINT UNSIGNED DEFAULT 0,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `comments_enabled` BOOLEAN DEFAULT TRUE,
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
    `media_type` ENUM('image', 'video', 'document', 'audio') NOT NULL,
    `width` INT UNSIGNED,
    `height` INT UNSIGNED,
    `duration` INT UNSIGNED,
    `thumbnail_path` VARCHAR(500),
    `is_processed` BOOLEAN DEFAULT FALSE,
    `extra_data` JSON,
    `hash` VARCHAR(64),
    `folder_type` VARCHAR(50),
    `related_id` BIGINT UNSIGNED,
    `is_public` BOOLEAN DEFAULT TRUE,
    `deleted_at` TIMESTAMP NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_file_path` (`file_path`),
    KEY `idx_media_type` (`media_type`),
    KEY `idx_hash` (`hash`),
    KEY `idx_folder_related` (`folder_type`, `related_id`),
    KEY `idx_created_at` (`created_at`),
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
    `visibility` ENUM('PUBLIC', 'FRIENDS', 'PRIVATE') DEFAULT 'PRIVATE',
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
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `friend_id` BIGINT UNSIGNED NOT NULL,
    `status` ENUM('pending', 'accepted', 'rejected', 'blocked') DEFAULT 'pending',
    `message` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `rejected_at` TIMESTAMP NULL DEFAULT NULL,
    `rejection_reason` TEXT DEFAULT NULL,
    `reason` TEXT DEFAULT NULL,
    `accepted_at` TIMESTAMP NULL DEFAULT NULL,
    --PRIMARY KEY (`user_id`, `friend_id`),
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_user_friend` (`user_id`, `friend_id`),
    KEY `idx_friend_status` (`friend_id`, `status`),
    CONSTRAINT `fk_friendships_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_friendships_friend` FOREIGN KEY (`friend_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 關注關係表
CREATE TABLE IF NOT EXISTS `follows` (
    `follower_id` BIGINT UNSIGNED NOT NULL,
    `following_id` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    `quoted_comment_id` BIGINT UNSIGNED DEFAULT NULL,
    `content` TEXT NOT NULL,
    `like_count` INT UNSIGNED DEFAULT 0,
    `reply_count` INT UNSIGNED DEFAULT 0,
    `last_reply_at` DATETIME DEFAULT NULL,
    `is_deleted` BOOLEAN DEFAULT FALSE,
    `deleted_by` BIGINT UNSIGNED DEFAULT NULL,
    `deleted_at` DATETIME DEFAULT NULL,
    `deletion_reason` VARCHAR(255) DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_post_created` (`post_id`, `created_at`),
    KEY `idx_comments_deleted` (`is_deleted`, `post_id`),
    KEY `idx_comments_likes` (`like_count` DESC),
    KEY `idx_comments_replies` (`last_reply_at` DESC),
    FULLTEXT KEY `idx_comments_fulltext` (`content`),
    CONSTRAINT `fk_comments_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_post` FOREIGN KEY (`post_id`) REFERENCES `posts` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_parent` FOREIGN KEY (`parent_id`) REFERENCES `comments` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comments_quoted` FOREIGN KEY (`quoted_comment_id`) REFERENCES `comments` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_comments_deleted_by` FOREIGN KEY (`deleted_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `comment_likes` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `comment_id` BIGINT UNSIGNED NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_user_comment` (`user_id`, `comment_id`),
    KEY `idx_comment_created` (`comment_id`, `created_at`),
    CONSTRAINT `fk_comment_likes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_comment_likes_comment` FOREIGN KEY (`comment_id`) REFERENCES `comments` (`id`) ON DELETE CASCADE
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
    `emergency_phone` VARCHAR(20) DEFAULT NULL,
    `email` VARCHAR(255) DEFAULT NULL,
    `website` VARCHAR(255) DEFAULT NULL,
    `address` JSON DEFAULT NULL,
    `latitude` DECIMAL(10, 8) DEFAULT NULL,
    `longitude` DECIMAL(11, 8) DEFAULT NULL,
    `country` VARCHAR(100) NOT NULL DEFAULT 'Hong Kong',
    `city` VARCHAR(100) DEFAULT NULL,
    `business_hours` JSON DEFAULT NULL COMMENT '營業時間格式: {"monday": {"open": "09:00", "close": "18:00", "is_closed": false}, ...}',
    `is_24_hours` BOOLEAN DEFAULT FALSE,
    `is_verified` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_clinic_location_country` (`country`, `latitude`, `longitude`),
    KEY `idx_location` (`latitude`, `longitude`),
    KEY `idx_country_city` (`country`, `city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 診所可治療品種表
CREATE TABLE IF NOT EXISTS `clinic_treatable_species` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `clinic_id` BIGINT UNSIGNED NOT NULL,
    `species` ENUM('dog', 'cat', 'bird', 'rabbit', 'hamster', 'fish', 'reptile', 'exotic', 'other') NOT NULL,
    `specific_breeds` JSON DEFAULT NULL COMMENT '特定品種列表',
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_clinic_species` (`clinic_id`, `species`),
    KEY `idx_species` (`species`),
    CONSTRAINT `fk_clinic_species_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 診所設備表（醫療儀器）
CREATE TABLE IF NOT EXISTS `clinic_equipment` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `clinic_id` BIGINT UNSIGNED NOT NULL,
    `equipment_type` ENUM('xray', 'ultrasound', 'mri', 'ct_scan', 'blood_test', 'urine_test', 'dental_xray', 'endoscope', 'ecg', 'surgical_laser', 'anesthesia_machine', 'other') NOT NULL,
    `equipment_name` VARCHAR(200) NOT NULL,
    `brand` VARCHAR(100) DEFAULT NULL,
    `model` VARCHAR(100) DEFAULT NULL,
    `purchase_date` DATE DEFAULT NULL,
    `last_maintenance_date` DATE DEFAULT NULL,
    `next_maintenance_date` DATE DEFAULT NULL,
    `is_operational` BOOLEAN DEFAULT TRUE,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_clinic_type` (`clinic_id`, `equipment_type`),
    KEY `idx_operational` (`is_operational`),
    CONSTRAINT `fk_clinic_equipment_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 診所服務項目表
CREATE TABLE IF NOT EXISTS `clinic_services` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `clinic_id` BIGINT UNSIGNED NOT NULL,
    `service_category` ENUM('consultation', 'surgery', 'vaccination', 'grooming', 'boarding', 'emergency', 'dental', 'diagnostic', 'other') NOT NULL,
    `service_name` VARCHAR(200) NOT NULL,
    `description` TEXT DEFAULT NULL,
    `price_min` DECIMAL(10,2) DEFAULT NULL,
    `price_max` DECIMAL(10,2) DEFAULT NULL,
    `duration_minutes` INT UNSIGNED DEFAULT NULL,
    `is_available` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_clinic_category` (`clinic_id`, `service_category`),
    KEY `idx_available` (`is_available`),
    CONSTRAINT `fk_clinic_services_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 診所評價表
CREATE TABLE IF NOT EXISTS `clinic_reviews` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `clinic_id` BIGINT UNSIGNED NOT NULL,
    `user_id` BIGINT UNSIGNED NOT NULL,
    `pet_id` BIGINT UNSIGNED DEFAULT NULL,
    `medical_record_id` BIGINT UNSIGNED DEFAULT NULL,
    `rating` TINYINT UNSIGNED NOT NULL CHECK (`rating` >= 1 AND `rating` <= 5),
    `service_rating` TINYINT UNSIGNED DEFAULT NULL CHECK (`service_rating` >= 1 AND `service_rating` <= 5),
    `price_rating` TINYINT UNSIGNED DEFAULT NULL CHECK (`price_rating` >= 1 AND `price_rating` <= 5),
    `facility_rating` TINYINT UNSIGNED DEFAULT NULL CHECK (`facility_rating` >= 1 AND `facility_rating` <= 5),
    `comment` TEXT DEFAULT NULL,
    `is_anonymous` BOOLEAN DEFAULT FALSE,
    `is_verified_visit` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_clinic_rating` (`clinic_id`, `rating`),
    KEY `idx_user` (`user_id`),
    CONSTRAINT `fk_clinic_reviews_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_clinic_reviews_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_clinic_reviews_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_clinic_reviews_record` FOREIGN KEY (`medical_record_id`) REFERENCES `pet_medical_records` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 獸醫師表
CREATE TABLE IF NOT EXISTS `veterinarians` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `clinic_id` BIGINT UNSIGNED DEFAULT NULL,
    `user_id` BIGINT UNSIGNED NULL,
    `name` VARCHAR(100) NOT NULL,
    `license_no` VARCHAR(100) DEFAULT NULL,
    `specialization` VARCHAR(200) DEFAULT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `email` VARCHAR(255) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_license` (`license_no`),
    CONSTRAINT `fk_veterinarians_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_veterinarians_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 獸醫的存取權限請求與狀態
CREATE TABLE IF NOT EXISTS `medical_record_permissions` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `pet_id` BIGINT UNSIGNED NOT NULL,
    `veterinarian_user_id` BIGINT UNSIGNED NOT NULL COMMENT '請求存取權限的獸醫用戶ID',
    `owner_user_id` BIGINT UNSIGNED NOT NULL COMMENT '寵物擁有者的用戶ID',
    `status` ENUM('pending', 'granted', 'rejected', 'revoked') NOT NULL DEFAULT 'pending',
    `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `responded_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_mrp_pet` FOREIGN KEY (`pet_id`) REFERENCES `pets` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_mrp_vet` FOREIGN KEY (`veterinarian_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_mrp_owner` FOREIGN KEY (`owner_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    UNIQUE KEY `_pet_vet_uc` (`pet_id`, `veterinarian_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 獸醫師當值表（支援多診所執業）
CREATE TABLE IF NOT EXISTS `veterinarian_schedules` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `veterinarian_id` BIGINT UNSIGNED NOT NULL,
    `clinic_id` BIGINT UNSIGNED NOT NULL,
    `day_of_week` ENUM('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday') NOT NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `effective_from` DATE DEFAULT NULL,
    `effective_until` DATE DEFAULT NULL,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_vet_schedule_active` (`is_active`, `effective_from`, `effective_until`),
    KEY `idx_vet_clinic` (`veterinarian_id`, `clinic_id`),
    KEY `idx_clinic_day` (`clinic_id`, `day_of_week`),
    KEY `idx_active_dates` (`is_active`, `effective_from`, `effective_until`),
    CONSTRAINT `fk_vet_schedule_vet` FOREIGN KEY (`veterinarian_id`) REFERENCES `veterinarians` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_vet_schedule_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 獸醫師特殊排班表（假日、特殊日期）
CREATE TABLE IF NOT EXISTS `veterinarian_special_schedules` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `veterinarian_id` BIGINT UNSIGNED NOT NULL,
    `clinic_id` BIGINT UNSIGNED NOT NULL,
    `schedule_date` DATE NOT NULL,
    `start_time` TIME DEFAULT NULL,
    `end_time` TIME DEFAULT NULL,
    `is_holiday` BOOLEAN DEFAULT FALSE,
    `notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_vet_clinic_date` (`veterinarian_id`, `clinic_id`, `schedule_date`),
    KEY `idx_date` (`schedule_date`),
    KEY `idx_clinic_date` (`clinic_id`, `schedule_date`),
    CONSTRAINT `fk_vet_special_vet` FOREIGN KEY (`veterinarian_id`) REFERENCES `veterinarians` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_vet_special_clinic` FOREIGN KEY (`clinic_id`) REFERENCES `veterinary_clinics` (`id`) ON DELETE CASCADE
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
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
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

-- 診所完整資訊視圖
CREATE OR REPLACE VIEW `v_clinic_full_info` AS
SELECT 
    c.*,
    COUNT(DISTINCT e.id) as equipment_count,
    COUNT(DISTINCT s.id) as service_count,
    COUNT(DISTINCT ts.species) as treatable_species_count,
    AVG(r.rating) as average_rating,
    COUNT(DISTINCT r.id) as review_count
FROM `veterinary_clinics` c
LEFT JOIN `clinic_equipment` e ON c.id = e.clinic_id AND e.is_operational = TRUE
LEFT JOIN `clinic_services` s ON c.id = s.clinic_id AND s.is_available = TRUE
LEFT JOIN `clinic_treatable_species` ts ON c.id = ts.clinic_id
LEFT JOIN `clinic_reviews` r ON c.id = r.clinic_id
GROUP BY c.id;

-- 獸醫師執業診所視圖
CREATE OR REPLACE VIEW `v_veterinarian_clinics` AS
SELECT 
    v.*,
    GROUP_CONCAT(DISTINCT c.name SEPARATOR ', ') as clinic_names,
    COUNT(DISTINCT vs.clinic_id) as clinic_count
FROM `veterinarians` v
LEFT JOIN `veterinarian_schedules` vs ON v.id = vs.veterinarian_id AND vs.is_active = TRUE
LEFT JOIN `veterinary_clinics` c ON vs.clinic_id = c.id
WHERE v.is_active = TRUE
GROUP BY v.id;

-- 重新開啟外鍵檢查
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================
-- 6. 建立距離計算函數（用於尋找最近的診所）
-- =============================================

DROP FUNCTION IF EXISTS `calculate_distance`;

DELIMITER //

CREATE FUNCTION `calculate_distance`(
    lat1 DECIMAL(10,8),
    lon1 DECIMAL(11,8),
    lat2 DECIMAL(10,8),
    lon2 DECIMAL(11,8)
) RETURNS DECIMAL(10,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE distance DECIMAL(10,2);
    
    -- Haversine formula
    SET distance = 6371 * 2 * ASIN(SQRT(
        POWER(SIN((lat2 - lat1) * PI() / 180 / 2), 2) +
        COS(lat1 * PI() / 180) * COS(lat2 * PI() / 180) *
        POWER(SIN((lon2 - lon1) * PI() / 180 / 2), 2)
    ));
    
    RETURN distance;
END//

DELIMITER ;

-- DELIMITER //

-- CREATE TRIGGER `update_parent_comment_stats` AFTER INSERT ON `comments`
-- FOR EACH ROW
-- BEGIN
--     IF NEW.parent_id IS NOT NULL THEN
--         UPDATE `comments` 
--         SET `reply_count` = `reply_count` + 1,
--             `last_reply_at` = NOW()
--         WHERE `id` = NEW.parent_id;
--     END IF;
-- END//

-- CREATE TRIGGER `update_comment_like_count` AFTER INSERT ON `comment_likes`
-- FOR EACH ROW
-- BEGIN
--     UPDATE `comments` 
--     SET `like_count` = `like_count` + 1
--     WHERE `id` = NEW.comment_id;
-- END//

-- CREATE TRIGGER `decrease_comment_like_count` AFTER DELETE ON `comment_likes`
-- FOR EACH ROW
-- BEGIN
--     UPDATE `comments` 
--     SET `like_count` = `like_count` - 1
--     WHERE `id` = OLD.comment_id AND `like_count` > 0;
-- END//

-- DELIMITER ;

-- 使用範例：尋找用戶附近的診所
-- SELECT 
--     c.*,
--     calculate_distance(u.location_latitude, u.location_longitude, c.latitude, c.longitude) AS distance_km
-- FROM veterinary_clinics c
-- CROSS JOIN users u
-- WHERE u.id = ? 
--     AND c.country = u.location_country
--     AND c.is_verified = TRUE
-- HAVING distance_km <= 50
-- ORDER BY distance_km ASC
-- LIMIT 10;