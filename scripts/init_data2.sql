-- =============================================
-- 寵物社交平台初始化數據
-- =============================================

-- 1. 插入預設角色
INSERT INTO `roles` (`name`, `display_name`, `description`, `is_system`) VALUES
('super_admin', '超級管理員', '擁有所有權限', TRUE),
('admin', '管理員', '一般管理權限', TRUE),
('merchant', '商戶', '可以販售商品', TRUE),
('veterinarian', '獸醫師', '可以管理醫療記錄', TRUE),
('user', '一般用戶', '基本用戶權限', TRUE),
('guest', '訪客', '僅可瀏覽公開內容', TRUE);

-- 2. 插入所有權限
INSERT INTO `permissions` (`module`, `action`, `name`, `description`) VALUES
-- 用戶模組權限
('user', 'create', 'user.create', '建立用戶'),
('user', 'read', 'user.read', '查看用戶'),
('user', 'update', 'user.update', '更新用戶'),
('user', 'delete', 'user.delete', '刪除用戶'),
('user', 'manage', 'user.manage', '管理所有用戶'),

-- 貼文模組權限
('post', 'create', 'post.create', '建立貼文'),
('post', 'read', 'post.read', '查看貼文'),
('post', 'update', 'post.update', '更新自己的貼文'),
('post', 'delete', 'post.delete', '刪除自己的貼文'),
('post', 'manage', 'post.manage', '管理所有貼文'),

-- 寵物模組權限
('pet', 'create', 'pet.create', '建立寵物資料'),
('pet', 'read', 'pet.read', '查看寵物資料'),
('pet', 'update', 'pet.update', '更新寵物資料'),
('pet', 'delete', 'pet.delete', '刪除寵物資料'),
('pet', 'manage', 'pet.manage', '管理所有寵物資料'),

-- 相簿模組權限
('album', 'create', 'album.create', '建立相簿'),
('album', 'read', 'album.read', '查看相簿'),
('album', 'update', 'album.update', '更新相簿'),
('album', 'delete', 'album.delete', '刪除相簿'),
('album', 'share', 'album.share', '分享相簿'),

-- 商品模組權限
('product', 'create', 'product.create', '建立商品'),
('product', 'read', 'product.read', '查看商品'),
('product', 'update', 'product.update', '更新商品'),
('product', 'delete', 'product.delete', '刪除商品'),
('product', 'manage', 'product.manage', '管理所有商品'),

-- 訂單模組權限
('order', 'create', 'order.create', '建立訂單'),
('order', 'read', 'order.read', '查看訂單'),
('order', 'update', 'order.update', '更新訂單'),
('order', 'cancel', 'order.cancel', '取消訂單'),
('order', 'manage', 'order.manage', '管理所有訂單'),

-- 商戶模組權限
('merchant', 'apply', 'merchant.apply', '申請成為商戶'),
('merchant', 'manage', 'merchant.manage', '管理商戶'),
('merchant', 'review', 'merchant.review', '審核商戶申請'),

-- 醫療記錄模組權限
('medical', 'create', 'medical.create', '建立醫療記錄'),
('medical', 'read', 'medical.read', '查看自己寵物的醫療記錄'),
('medical', 'update', 'medical.update', '更新醫療記錄'),
('medical', 'delete', 'medical.delete', '刪除醫療記錄'),
('medical', 'manage', 'medical.manage', '管理所有醫療記錄'),

-- 疫苗模組權限
('vaccine', 'create', 'vaccine.create', '建立疫苗記錄'),
('vaccine', 'read', 'vaccine.read', '查看疫苗記錄'),
('vaccine', 'update', 'vaccine.update', '更新疫苗記錄'),
('vaccine', 'manage', 'vaccine.manage', '管理疫苗類型'),

-- 通知模組權限
('notification', 'send', 'notification.send', '發送通知'),
('notification', 'manage', 'notification.manage', '管理通知'),

-- 管理模組權限
('admin', 'access', 'admin.access', '訪問管理後台'),
('admin', 'manage', 'admin.manage', '所有管理權限'),
('admin', 'export', 'admin.export', '匯出數據'),
('admin', 'import', 'admin.import', '匯入數據');

-- 3. 設置角色權限關聯
-- 超級管理員 - 所有權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'super_admin';

-- 管理員 - 除了某些特殊權限外的所有權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'admin' 
AND p.name NOT IN ('admin.manage', 'admin.import');

-- 商戶 - 商品相關權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'merchant' 
AND p.name IN (
    'product.create', 'product.read', 'product.update', 'product.delete',
    'order.read', 'order.update',
    'user.read', 'pet.read', 'post.create', 'post.read'
);

-- 獸醫師 - 醫療相關權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'veterinarian' 
AND p.name IN (
    'medical.create', 'medical.read', 'medical.update',
    'vaccine.create', 'vaccine.read', 'vaccine.update',
    'pet.read', 'user.read'
);

-- 一般用戶 - 基本權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'user' 
AND p.name IN (
    'user.read', 'user.update',
    'pet.create', 'pet.read', 'pet.update', 'pet.delete',
    'post.create', 'post.read', 'post.update', 'post.delete',
    'album.create', 'album.read', 'album.update', 'album.delete', 'album.share',
    'product.read', 'order.create', 'order.read',
    'medical.read', 'vaccine.read',
    'merchant.apply'
);

-- 訪客 - 唯讀權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'guest' 
AND p.action = 'read'
AND p.module NOT IN ('medical', 'order');

-- 4. 插入疫苗類型
INSERT INTO `vaccine_types` 
(`species`, `name`, `abbreviation`, `description`, `recommended_age_weeks`, `booster_interval_months`, `is_core`) 
VALUES
-- 狗疫苗
('dog', '犬瘟熱疫苗', 'CDV', '預防犬瘟熱病毒感染，是狗狗核心疫苗之一', 6, 12, TRUE),
('dog', '犬小病毒疫苗', 'CPV', '預防犬小病毒感染，可能導致嚴重腸胃炎', 6, 12, TRUE),
('dog', '犬傳染性肝炎疫苗', 'CAV', '預防犬傳染性肝炎，保護肝臟健康', 6, 12, TRUE),
('dog', '狂犬病疫苗', 'Rabies', '預防狂犬病，為法定必須施打疫苗', 12, 12, TRUE),
('dog', '犬舍咳疫苗', 'KC', '預防犬舍咳，適合經常接觸其他狗的犬隻', 8, 12, FALSE),
('dog', '萊姆病疫苗', 'Lyme', '預防由壁蝨傳播的萊姆病', 12, 12, FALSE),

-- 貓疫苗
('cat', '貓瘟疫苗', 'FPV', '預防貓瘟，是貓咪核心疫苗之一', 8, 12, TRUE),
('cat', '貓鼻氣管炎疫苗', 'FHV', '預防貓鼻氣管炎，保護呼吸道健康', 8, 12, TRUE),
('cat', '貓杯狀病毒疫苗', 'FCV', '預防貓杯狀病毒感染', 8, 12, TRUE),
('cat', '狂犬病疫苗', 'Rabies', '預防狂犬病，為法定必須施打疫苗', 12, 12, TRUE),
('cat', '貓白血病疫苗', 'FeLV', '預防貓白血病，建議外出貓施打', 8, 12, FALSE),
('cat', '貓愛滋病疫苗', 'FIV', '預防貓免疫缺陷病毒感染', 8, 12, FALSE),

-- 兔子疫苗
('rabbit', '兔出血症疫苗', 'RHD', '預防兔出血症病毒感染', 5, 12, TRUE),
('rabbit', '黏液瘤病疫苗', 'Myxo', '預防黏液瘤病', 5, 12, TRUE);

-- 5. 插入商品分類
INSERT INTO `product_categories` 
(`name`, `slug`, `parent_id`, `description`, `is_active`, `display_order`) 
VALUES
-- 主分類
('寵物食品', 'pet-food', NULL, '各類寵物食品與營養品', TRUE, 1),
('寵物用品', 'pet-supplies', NULL, '寵物日常用品與配件', TRUE, 2),
('寵物玩具', 'pet-toys', NULL, '各類寵物玩具', TRUE, 3),
('寵物保健', 'pet-health', NULL, '寵物保健與醫療用品', TRUE, 4),
('寵物美容', 'pet-grooming', NULL, '寵物美容與清潔用品', TRUE, 5),
('寵物服飾', 'pet-clothing', NULL, '寵物服裝與配飾', TRUE, 6);

-- 插入子分類（需要在主分類插入後執行）
SET @food_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-food');
SET @supplies_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-supplies');
SET @toys_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-toys');
SET @health_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-health');

-- 寵物食品子分類
INSERT INTO `product_categories` 
(`name`, `slug`, `parent_id`, `description`, `is_active`, `display_order`) 
VALUES
('狗糧', 'dog-food', @food_id, '各類狗糧與狗零食', TRUE, 1),
('貓糧', 'cat-food', @food_id, '各類貓糧與貓零食', TRUE, 2),
('小動物糧食', 'small-pet-food', @food_id, '兔子、倉鼠等小動物食品', TRUE, 3),
('營養補充品', 'supplements', @food_id, '各類營養補充劑', TRUE, 4);

-- 寵物用品子分類
INSERT INTO `product_categories` 
(`name`, `slug`, `parent_id`, `description`, `is_active`, `display_order`) 
VALUES
('窩墊床具', 'beds-mats', @supplies_id, '寵物床墊與休息用品', TRUE, 1),
('餐具水具', 'bowls-feeders', @supplies_id, '寵物餐具與飲水器', TRUE, 2),
('牽繩項圈', 'leashes-collars', @supplies_id, '牽繩、項圈與胸背帶', TRUE, 3),
('外出用品', 'travel-carriers', @supplies_id, '外出籠與運輸用品', TRUE, 4);

-- 6. 創建預設管理員帳號 (密碼: admin123456)
INSERT INTO `users` 
(`username`, `email`, `password_hash`, `display_name`, `is_active`, `is_verified`) 
VALUES
('admin', 'admin@oss.com', '$2b$12$5sPwKHusWcVv51j0sI2.2uaLhvH7Ujjbmeo.x0a/UkgKIGiLVrKfW', '系統管理員', TRUE, TRUE);

-- 分配超級管理員角色給 admin
SET @admin_user_id = (SELECT id FROM `users` WHERE username = 'admin');
SET @super_admin_role_id = (SELECT id FROM `roles` WHERE name = 'super_admin');

INSERT INTO `user_roles` (`user_id`, `role_id`) 
VALUES (@admin_user_id, @super_admin_role_id);

-- 7. 創建示例獸醫診所
INSERT INTO `veterinary_clinics` 
(`name`, `license_no`, `phone`, `email`, `address`, `latitude`, `longitude`, `is_verified`) 
VALUES
('愛心動物醫院', 'VET-2024-001', '02-1234-5678', 'info@lovepet.com', 
 '{"city": "台北市", "district": "大安區", "street": "忠孝東路三段100號"}', 
 25.0418, 121.5435, TRUE),
('快樂寵物診所', 'VET-2024-002', '02-2345-6789', 'contact@happypet.com', 
 '{"city": "台北市", "district": "信義區", "street": "信義路四段200號"}', 
 25.0335, 121.5608, TRUE);

-- 8. 插入一些示例標籤
INSERT INTO `tags` (`name`, `usage_count`) VALUES
('狗狗', 100),
('貓咪', 95),
('可愛', 80),
('萌寵', 75),
('日常', 70),
('玩耍', 65),
('睡覺', 60),
('吃飯', 55),
('散步', 50),
('訓練', 45);