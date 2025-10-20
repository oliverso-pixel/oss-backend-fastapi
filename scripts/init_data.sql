-- =============================================
-- 寵物社交平台初始化數據
-- =============================================

-- 1. 插入預設角色
INSERT INTO `roles` (`name`, `display_name`, `description`, `is_system`) VALUES
('super_admin', '超級管理員', '擁有所有權限', TRUE),
('admin', '管理員', '一般管理權限', TRUE),
('merchant', '商戶', '可以販售商品', TRUE),
('veterinarian', '獸醫師', '可以管理醫療記錄', TRUE),
('clinic_admin', '診所管理員', '管理診所資訊與獸醫師', TRUE),
('user', '一般用戶', '基本用戶權限', TRUE),
('vip_user', 'VIP用戶', '進階用戶權限', TRUE),
('guest', '訪客', '僅可瀏覽公開內容', TRUE);

-- 2. 插入所有權限
INSERT INTO `permissions` (`module`, `action`, `name`, `description`) VALUES
-- 用戶模組權限
('user', 'create', 'user.create', '建立用戶'),
('user', 'read', 'user.read', '查看用戶'),
('user', 'update', 'user.update', '更新用戶'),
('user', 'delete', 'user.delete', '刪除用戶'),
('user', 'manage', 'user.manage', '管理所有用戶'),
('user', 'export', 'user.export', '匯出用戶資料'),

-- 貼文模組權限
('post', 'create', 'post.create', '建立貼文'),
('post', 'read', 'post.read', '查看貼文'),
('post', 'update', 'post.update', '更新自己的貼文'),
('post', 'delete', 'post.delete', '刪除自己的貼文'),
('post', 'manage', 'post.manage', '管理所有貼文'),
('post', 'pin', 'post.pin', '置頂貼文'),

-- 寵物模組權限
('pet', 'create', 'pet.create', '建立寵物資料'),
('pet', 'read', 'pet.read', '查看寵物資料'),
('pet', 'update', 'pet.update', '更新寵物資料'),
('pet', 'delete', 'pet.delete', '刪除寵物資料'),
('pet', 'transfer', 'pet.transfer', '轉移寵物'),
('pet', 'manage', 'pet.manage', '管理所有寵物資料'),

-- 相簿模組權限
('album', 'create', 'album.create', '建立相簿'),
('album', 'read', 'album.read', '查看相簿'),
('album', 'update', 'album.update', '更新相簿'),
('album', 'delete', 'album.delete', '刪除相簿'),
('album', 'share', 'album.share', '分享相簿'),
('album', 'manage', 'album.manage', '管理所有相簿'),

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
('order', 'export', 'order.export', '匯出訂單資料'),

-- 商戶模組權限
('merchant', 'apply', 'merchant.apply', '申請成為商戶'),
('merchant', 'manage', 'merchant.manage', '管理商戶'),
('merchant', 'review', 'merchant.review', '審核商戶申請'),
('merchant', 'suspend', 'merchant.suspend', '暫停商戶資格'),

-- 診所模組權限
('clinic', 'create', 'clinic.create', '建立診所'),
('clinic', 'read', 'clinic.read', '查看診所資訊'),
('clinic', 'update', 'clinic.update', '更新診所資訊'),
('clinic', 'manage', 'clinic.manage', '管理所有診所'),
('clinic', 'verify', 'clinic.verify', '驗證診所資格'),

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
('notification', 'broadcast', 'notification.broadcast', '廣播通知'),
('notification', 'manage', 'notification.manage', '管理通知'),

-- 管理模組權限
('admin', 'access', 'admin.access', '訪問管理後台'),
('admin', 'manage', 'admin.manage', '所有管理權限'),
('admin', 'export', 'admin.export', '匯出數據'),
('admin', 'import', 'admin.import', '匯入數據'),
('admin', 'audit', 'admin.audit', '查看審計日誌');

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
    'user.read', 'pet.read', 'post.create', 'post.read', 'post.update', 'post.delete',
    'album.create', 'album.read', 'album.update', 'album.delete'
);

-- 獸醫師 - 醫療相關權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'veterinarian' 
AND p.name IN (
    'medical.create', 'medical.read', 'medical.update',
    'vaccine.create', 'vaccine.read', 'vaccine.update',
    'pet.read', 'user.read',
    'clinic.read', 'clinic.update'
);

-- 診所管理員 - 診所管理權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'clinic_admin' 
AND p.name IN (
    'clinic.read', 'clinic.update',
    'medical.create', 'medical.read', 'medical.update', 'medical.manage',
    'vaccine.create', 'vaccine.read', 'vaccine.update',
    'veterinarian.manage',
    'user.read', 'pet.read'
);

-- VIP用戶 - 進階權限
INSERT INTO `role_permissions` (`role_id`, `permission_id`)
SELECT r.id, p.id FROM `roles` r 
CROSS JOIN `permissions` p 
WHERE r.name = 'vip_user' 
AND p.name IN (
    'user.read', 'user.update', 'user.export',
    'pet.create', 'pet.read', 'pet.update', 'pet.delete', 'pet.transfer',
    'post.create', 'post.read', 'post.update', 'post.delete',
    'album.create', 'album.read', 'album.update', 'album.delete', 'album.share',
    'product.read', 'order.create', 'order.read', 'order.cancel',
    'medical.read', 'vaccine.read',
    'merchant.apply'
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
AND p.module NOT IN ('medical', 'order', 'admin');

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
('dog', '犬冠狀病毒疫苗', 'CCV', '預防犬冠狀病毒感染', 6, 12, FALSE),

-- 貓疫苗
('cat', '貓瘟疫苗', 'FPV', '預防貓瘟，是貓咪核心疫苗之一', 8, 12, TRUE),
('cat', '貓鼻氣管炎疫苗', 'FHV', '預防貓鼻氣管炎，保護呼吸道健康', 8, 12, TRUE),
('cat', '貓杯狀病毒疫苗', 'FCV', '預防貓杯狀病毒感染', 8, 12, TRUE),
('cat', '狂犬病疫苗', 'Rabies', '預防狂犬病，為法定必須施打疫苗', 12, 12, TRUE),
('cat', '貓白血病疫苗', 'FeLV', '預防貓白血病，建議外出貓施打', 8, 12, FALSE),
('cat', '貓愛滋病疫苗', 'FIV', '預防貓免疫缺陷病毒感染', 8, 12, FALSE),
('cat', '貓傳染性腹膜炎疫苗', 'FIP', '預防貓傳染性腹膜炎', 16, 12, FALSE),

-- 兔子疫苗
('rabbit', '兔出血症疫苗', 'RHD', '預防兔出血症病毒感染', 5, 12, TRUE),
('rabbit', '黏液瘤病疫苗', 'Myxo', '預防黏液瘤病', 5, 12, TRUE),
('rabbit', '兔巴斯德桿菌疫苗', 'Pasteurella', '預防巴斯德桿菌感染', 4, 6, FALSE),

-- 其他寵物疫苗
('other', '雪貂犬瘟熱疫苗', 'Ferret-CDV', '預防雪貂犬瘟熱', 8, 12, TRUE),
('other', '雪貂狂犬病疫苗', 'Ferret-Rabies', '預防雪貂狂犬病', 12, 12, TRUE);

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
('寵物服飾', 'pet-clothing', NULL, '寵物服裝與配飾', TRUE, 6),
('寵物居家', 'pet-home', NULL, '寵物居家用品', TRUE, 7),
('寵物訓練', 'pet-training', NULL, '寵物訓練用品', TRUE, 8);

-- 插入子分類（需要在主分類插入後執行）
SET @food_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-food');
SET @supplies_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-supplies');
SET @toys_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-toys');
SET @health_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-health');
SET @grooming_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-grooming');
SET @clothing_id = (SELECT id FROM `product_categories` WHERE slug = 'pet-clothing');

-- 寵物食品子分類
INSERT INTO `product_categories` 
(`name`, `slug`, `parent_id`, `description`, `is_active`, `display_order`) 
VALUES
('狗糧', 'dog-food', @food_id, '各類狗糧與狗零食', TRUE, 1),
('貓糧', 'cat-food', @food_id, '各類貓糧與貓零食', TRUE, 2),
('小動物糧食', 'small-pet-food', @food_id, '兔子、倉鼠等小動物食品', TRUE, 3),
('鳥類飼料', 'bird-food', @food_id, '各類鳥類飼料', TRUE, 4),
('營養補充品', 'supplements', @food_id, '各類營養補充劑', TRUE, 5),
('處方飼料', 'prescription-food', @food_id, '獸醫處方飼料', TRUE, 6);

-- 寵物用品子分類
INSERT INTO `product_categories` 
(`name`, `slug`, `parent_id`, `description`, `is_active`, `display_order`) 
VALUES
('窩墊床具', 'beds-mats', @supplies_id, '寵物床墊與休息用品', TRUE, 1),
('餐具水具', 'bowls-feeders', @supplies_id, '寵物餐具與飲水器', TRUE, 2),
('牽繩項圈', 'leashes-collars', @supplies_id, '牽繩、項圈與胸背帶', TRUE, 3),
('外出用品', 'travel-carriers', @supplies_id, '外出籠與運輸用品', TRUE, 4),
('貓砂貓廁', 'litter-boxes', @supplies_id, '貓砂與貓廁所', TRUE, 5);

-- 6. 創建測試用戶帳號
-- 密碼統一為: admin23456 (hash: $2b$12$YourHashHere)
INSERT INTO `users` 
(`username`, `email`, `password_hash`, `display_name`, `bio`, `phone`, `is_active`, `is_verified`, `location_city`, `location_country`) 
VALUES
('admin', 'admin@oss.com', '$2b$12$5sPwKHusWcVv51j0sI2.2uaLhvH7Ujjbmeo.x0a/UkgKIGiLVrKfW', '系統管理員', '平台管理員', '0912-345-678', TRUE, TRUE, '台北市', 'Taiwan'),
('testuser1', 'testuser1@example.com', '$2b$12$Xp0knHO1MEW3CI5rMbJFkuRAD/N6vIkXLiYL0ocg5bBHs9BE/krrO', '測試用戶一號', '我是寵物愛好者，家有兩隻可愛的狗狗', '0922-111-111', TRUE, TRUE, '台北市', 'Taiwan'),
('testuser2', 'testuser2@example.com', '$2b$12$Xp0knHO1MEW3CI5rMbJFkuRAD/N6vIkXLiYL0ocg5bBHs9BE/krrO', '測試用戶二號', '貓奴一枚，愛貓成痴', '0922-222-222', TRUE, TRUE, '新北市', 'Taiwan'),
('testuser3', 'testuser3@example.com', '$2b$12$Xp0knHO1MEW3CI5rMbJFkuRAD/N6vIkXLiYL0ocg5bBHs9BE/krrO', '測試用戶三號', '寵物商家，專營寵物用品', '0922-333-333', TRUE, TRUE, '台中市', 'Taiwan'),
('testuser4', 'testuser4@example.com', '$2b$12$Xp0knHO1MEW3CI5rMbJFkuRAD/N6vIkXLiYL0ocg5bBHs9BE/krrO', '測試用戶四號', '獸醫師，熱愛小動物', '0922-444-444', TRUE, TRUE, '高雄市', 'Taiwan'),
('vetdoctor', 'vet@example.com', '$2b$12$Xp0knHO1MEW3CI5rMbJFkuRAD/N6vIkXLiYL0ocg5bBHs9BE/krrO', '李獸醫', '執業獸醫師，專長小動物內科', '0922-555-555', TRUE, TRUE, '台北市', 'Taiwan'),
('petshop', 'shop@example.com', '$2b$12$Xp0knHO1MEW3CI5rMbJFkuRAD/N6vIkXLiYL0ocg5bBHs9BE/krrO', '萌寵小舖', '專營優質寵物用品', '0922-666-666', TRUE, TRUE, '台北市', 'Taiwan');

-- 7. 分配用戶角色
-- SET @admin_id = (SELECT id FROM `users` WHERE username = 'admin');
-- SET @user1_id = (SELECT id FROM `users` WHERE username = 'testuser1');
-- SET @user2_id = (SELECT id FROM `users` WHERE username = 'testuser2');
-- SET @user3_id = (SELECT id FROM `users` WHERE username = 'testuser3');
-- SET @user4_id = (SELECT id FROM `users` WHERE username = 'testuser4');
-- SET @vet_id = (SELECT id FROM `users` WHERE username = 'vetdoctor');
-- SET @shop_id = (SELECT id FROM `users` WHERE username = 'petshop');

SELECT @admin_id := id FROM `users` WHERE username = 'admin';
SELECT @user1_id := id FROM `users` WHERE username = 'testuser1';
SELECT @user2_id := id FROM `users` WHERE username = 'testuser2';
SELECT @user3_id := id FROM `users` WHERE username = 'testuser3';
SELECT @user4_id := id FROM `users` WHERE username = 'testuser4';
SELECT @vet_id := id FROM `users` WHERE username = 'vetdoctor';
SELECT @shop_id := id FROM `users` WHERE username = 'petshop';

SELECT @super_admin_role := id FROM `roles` WHERE name = 'super_admin';
SELECT @user_role := id FROM `roles` WHERE name = 'user';
SELECT @merchant_role := id FROM `roles` WHERE name = 'merchant';
SELECT @vet_role := id FROM `roles` WHERE name = 'veterinarian';
SELECT @vip_role := id FROM `roles` WHERE name = 'vip_user';

INSERT INTO `user_roles` (`user_id`, `role_id`) VALUES
(@admin_id, @super_admin_role),
(@user1_id, @user_role),
(@user2_id, @vip_role),
(@user3_id, @user_role),
(@user3_id, @merchant_role),
(@user4_id, @user_role),
(@user4_id, @vet_role),
(@vet_id, @vet_role),
(@shop_id, @merchant_role);

-- 8. 創建測試寵物
INSERT INTO `pets` 
(`user_id`, `name`, `species`, `breed`, `gender`, `birth_date`, `weight`, `description`, `privacy_level`) 
VALUES
(@user1_id, '小黃', 'dog', '黃金獵犬', 'male', '2020-05-15', 28.5, '活潑可愛的黃金獵犬，喜歡游泳', 'public'),
(@user1_id, '小黑', 'dog', '拉布拉多', 'female', '2021-03-20', 25.0, '溫柔的拉布拉多，很會撒嬌', 'public'),
(@user2_id, '咪咪', 'cat', '英國短毛貓', 'female', '2019-08-10', 4.5, '優雅的英短，愛吃愛睡', 'public'),
(@user2_id, '球球', 'cat', '橘貓', 'male', '2020-12-01', 6.2, '貪吃的橘貓，圓滾滾的', 'private'),
(@user4_id, '雪球', 'rabbit', '垂耳兔', 'female', '2022-02-14', 2.1, '可愛的垂耳兔，喜歡吃紅蘿蔔', 'public');

-- 9. 創建示例商戶
INSERT INTO `merchants` 
(`user_id`, `shop_name`, `shop_slug`, `business_type`, `description`, `contact_email`, `contact_phone`, `commission_rate`, `status`, `verified_at`, `verified_by`) 
VALUES
(@user3_id, '萌寵生活館', 'mengchong-life', 'individual', '提供優質寵物用品，讓毛孩生活更美好', 'mengchong@example.com', '0922-333-333', 10.00, 'approved', NOW(), @admin_id),
(@shop_id, '萌寵小舖', 'mengchong-shop', 'company', '專業寵物用品店，品質保證', 'shop@example.com', '0922-666-666', 8.00, 'approved', NOW(), @admin_id);

-- 10. 創建更多獸醫診所
INSERT INTO `veterinary_clinics` 
(`name`, `license_no`, `phone`, `email`, `address`, `latitude`, `longitude`, `country`, `city`, `is_verified`, `is_24_hours`, `business_hours`) 
VALUES
('愛心動物醫院', 'VET-2024-001', '02-1234-5678', 'info@lovepet.com', 
 '{"city": "台北市", "district": "大安區", "street": "忠孝東路三段100號"}', 
 25.0418, 121.5435, 'Taiwan', '台北市', TRUE, FALSE,
 '{"monday": {"open": "09:00", "close": "21:00", "is_closed": false}, "tuesday": {"open": "09:00", "close": "21:00", "is_closed": false}, "wednesday": {"open": "09:00", "close": "21:00", "is_closed": false}, "thursday": {"open": "09:00", "close": "21:00", "is_closed": false}, "friday": {"open": "09:00", "close": "21:00", "is_closed": false}, "saturday": {"open": "09:00", "close": "18:00", "is_closed": false}, "sunday": {"open": "10:00", "close": "17:00", "is_closed": false}}'),

('快樂寵物診所', 'VET-2024-002', '02-2345-6789', 'contact@happypet.com', 
 '{"city": "台北市", "district": "信義區", "street": "信義路四段200號"}', 
 25.0335, 121.5608, 'Taiwan', '台北市', TRUE, FALSE,
 '{"monday": {"open": "10:00", "close": "20:00", "is_closed": false}, "tuesday": {"open": "10:00", "close": "20:00", "is_closed": false}, "wednesday": {"open": "10:00", "close": "20:00", "is_closed": false}, "thursday": {"open": "10:00", "close": "20:00", "is_closed": false}, "friday": {"open": "10:00", "close": "20:00", "is_closed": false}, "saturday": {"open": "10:00", "close": "17:00", "is_closed": false}, "sunday": {"is_closed": true}}'),

('24小時急診動物醫院', 'VET-2024-003', '02-3456-7890', 'emergency@24pet.com', 
 '{"city": "台北市", "district": "中山區", "street": "民生東路二段50號"}', 
 25.0577, 121.5265, 'Taiwan', '台北市', TRUE, TRUE, NULL),

('仁愛動物醫院', 'VET-2024-004', '04-1234-5678', 'care@renai-vet.com', 
 '{"city": "台中市", "district": "西區", "street": "台灣大道二段100號"}', 
 24.1477, 120.6736, 'Taiwan', '台中市', TRUE, FALSE,
 '{"monday": {"open": "09:00", "close": "19:00", "is_closed": false}, "tuesday": {"open": "09:00", "close": "19:00", "is_closed": false}, "wednesday": {"is_closed": true}, "thursday": {"open": "09:00", "close": "19:00", "is_closed": false}, "friday": {"open": "09:00", "close": "19:00", "is_closed": false}, "saturday": {"open": "09:00", "close": "17:00", "is_closed": false}, "sunday": {"is_closed": true}}');

-- 11. 設定診所可治療品種
SET @clinic1_id = (SELECT id FROM `veterinary_clinics` WHERE license_no = 'VET-2024-001');
SET @clinic2_id = (SELECT id FROM `veterinary_clinics` WHERE license_no = 'VET-2024-002');
SET @clinic3_id = (SELECT id FROM `veterinary_clinics` WHERE license_no = 'VET-2024-003');
SET @clinic4_id = (SELECT id FROM `veterinary_clinics` WHERE license_no = 'VET-2024-004');

INSERT INTO `clinic_treatable_species` (`clinic_id`, `species`, `specific_breeds`) VALUES
(@clinic1_id, 'dog', '["所有犬種"]'),
(@clinic1_id, 'cat', '["所有貓種"]'),
(@clinic1_id, 'rabbit', NULL),
(@clinic2_id, 'dog', '["小型犬", "中型犬"]'),
(@clinic2_id, 'cat', '["所有貓種"]'),
(@clinic3_id, 'dog', '["所有犬種"]'),
(@clinic3_id, 'cat', '["所有貓種"]'),
(@clinic3_id, 'exotic', '["刺蝟", "蜜袋鼯", "龍貓"]'),
(@clinic4_id, 'dog', '["所有犬種"]'),
(@clinic4_id, 'cat', '["所有貓種"]'),
(@clinic4_id, 'bird', '["鸚鵡", "文鳥", "金絲雀"]');

-- 12. 設定診所設備
INSERT INTO `clinic_equipment` (`clinic_id`, `equipment_type`, `equipment_name`, `brand`, `is_operational`) VALUES
(@clinic1_id, 'xray', '數位X光機', 'Canon', TRUE),
(@clinic1_id, 'ultrasound', '超音波掃描儀', 'GE Healthcare', TRUE),
(@clinic1_id, 'blood_test', '血液分析儀', 'IDEXX', TRUE),
(@clinic2_id, 'xray', 'X光機', 'Siemens', TRUE),
(@clinic2_id, 'dental_xray', '牙科X光機', 'Sopix', TRUE),
(@clinic3_id, 'xray', '數位X光機', 'Canon', TRUE),
(@clinic3_id, 'ultrasound', '超音波掃描儀', 'Mindray', TRUE),
(@clinic3_id, 'ct_scan', 'CT掃描儀', 'GE Healthcare', TRUE),
(@clinic3_id, 'anesthesia_machine', '麻醉機', 'Midmark', TRUE),
(@clinic4_id, 'xray', 'X光機', 'Fujifilm', TRUE),
(@clinic4_id, 'blood_test', '血液生化分析儀', 'Abaxis', TRUE);

-- 13. 創建獸醫師
INSERT INTO `veterinarians` 
(`clinic_id`, `name`, `license_no`, `specialization`, `phone`, `email`, `is_active`) 
VALUES
(@clinic1_id, '王大明', 'VET-LIC-001', '小動物內科、心臟科', '0911-111-111', 'wang@lovepet.com', TRUE),
(@clinic1_id, '李小美', 'VET-LIC-002', '小動物外科、骨科', '0911-222-222', 'lee@lovepet.com', TRUE),
(@clinic2_id, '陳志強', 'VET-LIC-003', '貓科專門、內科', '0911-333-333', 'chen@happypet.com', TRUE),
(@clinic3_id, '林醫師', 'VET-LIC-004', '急診醫學、重症加護', '0911-444-444', 'lin@24pet.com', TRUE),
(@clinic4_id, '張醫師', 'VET-LIC-005', '鳥類醫學、異寵專科', '0911-555-555', 'zhang@renai-vet.com', TRUE);

-- 將 testuser4 設定為獸醫師
SET @vet_user_id = (SELECT id FROM `users` WHERE username = 'testuser4');
INSERT INTO `veterinarians` 
(`clinic_id`, `name`, `license_no`, `specialization`, `phone`, `email`, `is_active`) 
VALUES
(@clinic1_id, '測試獸醫四號', 'VET-LIC-TEST', '小動物內科', '0922-444-444', 'testuser4@example.com', TRUE);

-- 14. 插入更多標籤
INSERT INTO `tags` (`name`, `usage_count`) VALUES
('狗狗', 150),
('貓咪', 145),
('可愛', 120),
('萌寵', 115),
('日常', 110),
('玩耍', 95),
('睡覺', 90),
('吃飯', 85),
('散步', 80),
('訓練', 75),
('洗澡', 70),
('搞笑', 65),
('治癒', 60),
('陪伴', 55),
('健康', 50),
('美容', 45),
('旅行', 40),
('生日', 35),
('節日', 30),
('新成員', 25);

-- 15. 創建示例貼文
SET @pet1_id = (SELECT id FROM `pets` WHERE name = '小黃' AND user_id = @user1_id);
SET @pet2_id = (SELECT id FROM `pets` WHERE name = '咪咪' AND user_id = @user2_id);

INSERT INTO `posts` (`user_id`, `pet_id`, `content`, `visibility`, `location`, `view_count`) VALUES
(@user1_id, @pet1_id, '今天帶小黃去公園玩，他超開心的！#狗狗 #散步 #日常', 'public', '大安森林公園', 50),
(@user1_id, @pet1_id, '小黃第一次游泳，天生的游泳健將！#狗狗 #游泳 #可愛', 'public', '寵物游泳池', 120),
(@user2_id, @pet2_id, '咪咪的新睡姿，也太可愛了吧！#貓咪 #睡覺 #萌寵', 'public', NULL, 200),
(@user2_id, @pet2_id, '今天帶咪咪去打疫苗，表現很勇敢喔！#貓咪 #健康 #疫苗', 'friends', '愛心動物醫院', 30);

-- 添加評論測試數據
SET @post1_id = (SELECT id FROM `posts` WHERE content LIKE '今天帶小黃去公園玩%' LIMIT 1);
SET @post2_id = (SELECT id FROM `posts` WHERE content LIKE '小黃第一次游泳%' LIMIT 1);
SET @post3_id = (SELECT id FROM `posts` WHERE content LIKE '咪咪的新睡姿%' LIMIT 1);

-- 插入測試評論
INSERT INTO `comments` (`user_id`, `post_id`, `content`, `created_at`) VALUES
(@user2_id, @post1_id, '小黃看起來真的很開心！', NOW()),
(@user3_id, @post1_id, '下次可以一起去公園遛狗', NOW() + INTERVAL 1 MINUTE),
(@user4_id, @post2_id, '游泳對狗狗很好的運動', NOW() + INTERVAL 2 MINUTE),
(@user1_id, @post3_id, '貓咪的睡姿都很奇特哈哈', NOW() + INTERVAL 3 MINUTE);

-- 添加回覆評論
SET @comment1_id = (SELECT id FROM `comments` WHERE content = '小黃看起來真的很開心！' LIMIT 1);
SET @comment2_id = (SELECT id FROM `comments` WHERE content = '下次可以一起去公園遛狗' LIMIT 1);

INSERT INTO `comments` (`user_id`, `post_id`, `parent_id`, `content`, `created_at`) VALUES
(@user1_id, @post1_id, @comment1_id, '是啊！他最喜歡去公園了', NOW() + INTERVAL 5 MINUTE),
(@user1_id, @post1_id, @comment2_id, '好啊！週末一起去', NOW() + INTERVAL 6 MINUTE);

-- 添加引用評論
INSERT INTO `comments` (`user_id`, `post_id`, `quoted_comment_id`, `content`, `created_at`) VALUES
(@user4_id, @post1_id, @comment1_id, '引用：小黃看起來真的很開心！\n\n確實，狗狗在戶外都特別活潑', NOW() + INTERVAL 10 MINUTE);

-- 添加評論按讚
INSERT INTO `comment_likes` (`user_id`, `comment_id`) VALUES
(@user1_id, @comment1_id),
(@user3_id, @comment1_id),
(@user4_id, @comment1_id),
(@user2_id, @comment2_id);

-- 更新一個貼文為關閉評論
-- UPDATE `posts` SET `comments_enabled` = FALSE WHERE id = @post3_id;

-- 添加一個被刪除的評論範例
INSERT INTO `comments` (`user_id`, `post_id`, `content`, `is_deleted`, `deleted_by`, `deleted_at`, `deletion_reason`, `created_at`) VALUES
(@user3_id, @post1_id, '這個內容已被刪除', TRUE, @admin_id, NOW(), '違反社群規範', NOW() - INTERVAL 1 HOUR);

-- 16. 創建通知範例
INSERT INTO `notifications` (`user_id`, `type`, `title`, `content`, `data`) VALUES
(@user1_id, 'follow', '新的關注者', 'testuser2 開始關注你了', '{"follower_id": 2}'),
(@user2_id, 'like', '貼文被按讚', '你的貼文獲得了新的讚', '{"post_id": 3, "user_id": 1}'),
(@user3_id, 'order', '新訂單', '你有一筆新的訂單', '{"order_id": 1}'),
(@user4_id, 'appointment', '預約提醒', '明天有一個寵物看診預約', '{"appointment_id": 1}');

-- 17. 創建聊天室範例
INSERT INTO `chat_rooms` (`type`, `name`) VALUES
('private', NULL),
('group', '寵物愛好者群組');

-- 設定聊天室成員
SET @private_room_id = (SELECT id FROM `chat_rooms` WHERE type = 'private' LIMIT 1);
SET @group_room_id = (SELECT id FROM `chat_rooms` WHERE type = 'group' LIMIT 1);

INSERT INTO `chat_room_members` (`room_id`, `user_id`, `role`) VALUES
(@private_room_id, @user1_id, 'member'),
(@private_room_id, @user2_id, 'member'),
(@group_room_id, @user1_id, 'admin'),
(@group_room_id, @user2_id, 'member'),
(@group_room_id, @user3_id, 'member'),
(@group_room_id, @user4_id, 'member');

-- 18. 設定好友關係
INSERT INTO `friendships` (`user_id`, `friend_id`, `status`, `accepted_at`) VALUES
(@user1_id, @user2_id, 'accepted', NOW()),
(@user2_id, @user1_id, 'accepted', NOW()),
(@user1_id, @user3_id, 'accepted', NOW()),
(@user3_id, @user1_id, 'accepted', NOW());

-- 19. 設定關注關係
INSERT INTO `follows` (`follower_id`, `following_id`) VALUES
(@user2_id, @user1_id),
(@user3_id, @user1_id),
(@user4_id, @user1_id),
(@user1_id, @user2_id),
(@user3_id, @user2_id);

-- 20. 創建診所服務項目
INSERT INTO `clinic_services` 
(`clinic_id`, `service_category`, `service_name`, `description`, `price_min`, `price_max`, `duration_minutes`) 
VALUES
(@clinic1_id, 'consultation', '一般門診', '基本健康檢查與諮詢', 300, 500, 30),
(@clinic1_id, 'vaccination', '預防針注射', '各類疫苗施打', 500, 1500, 20),
(@clinic1_id, 'surgery', '結紮手術', '犬貓結紮手術', 2000, 5000, 120),
(@clinic2_id, 'consultation', '貓咪專科門診', '貓咪專門診療', 400, 600, 30),
(@clinic2_id, 'grooming', '基礎美容', '洗澡、修剪指甲', 500, 1000, 60),
(@clinic3_id, 'emergency', '急診服務', '24小時緊急醫療', 1000, 5000, NULL),
(@clinic3_id, 'diagnostic', 'X光檢查', '數位X光診斷', 800, 1500, 30);

-- 完成初始化
SELECT '初始化數據完成！' as message;