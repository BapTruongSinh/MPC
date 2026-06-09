-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: retech_db
-- ------------------------------------------------------
-- Server version	9.6.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'd9697354-1ee8-11f1-b216-3c219c7bc94b:1-69093';

--
-- Table structure for table `products_product`
--

DROP TABLE IF EXISTS `products_product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products_product` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_deleted` tinyint(1) NOT NULL,
  `slug` varchar(50) DEFAULT NULL,
  `name` varchar(225) NOT NULL,
  `description` longtext,
  `price` decimal(12,0) NOT NULL,
  `original_price` decimal(12,0) DEFAULT NULL,
  `condition` varchar(20) NOT NULL,
  `warranty_period` int NOT NULL,
  `main_image` varchar(100) DEFAULT NULL,
  `is_sold` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `brand_id` bigint DEFAULT NULL,
  `category_id` bigint DEFAULT NULL,
  `seller_id` bigint NOT NULL,
  `main_image_url` longtext,
  `ram` varchar(50) DEFAULT NULL,
  `storage` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `products_product_is_deleted_9777f713` (`is_deleted`),
  KEY `products_product_is_sold_aaacac6e` (`is_sold`),
  KEY `products_product_created_at_3c9cea31` (`created_at`),
  KEY `products_product_seller_id_07afb1e3_fk_users_user_id` (`seller_id`),
  KEY `products_pr_slug_3edc0c_idx` (`slug`),
  KEY `products_pr_categor_9edb3d_idx` (`category_id`),
  KEY `products_pr_brand_i_dc6890_idx` (`brand_id`),
  KEY `products_pr_is_sold_27d418_idx` (`is_sold`),
  KEY `products_pr_created_52f0d7_idx` (`created_at`),
  KEY `products_pr_price_9b1a5f_idx` (`price`),
  CONSTRAINT `products_product_brand_id_3e2e8fd1_fk_products_brand_id` FOREIGN KEY (`brand_id`) REFERENCES `products_brand` (`id`),
  CONSTRAINT `products_product_category_id_9b594869_fk_products_category_id` FOREIGN KEY (`category_id`) REFERENCES `products_category` (`id`),
  CONSTRAINT `products_product_seller_id_07afb1e3_fk_users_user_id` FOREIGN KEY (`seller_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `products_product`
--

LOCK TABLES `products_product` WRITE;
/*!40000 ALTER TABLE `products_product` DISABLE KEYS */;
INSERT INTO `products_product` VALUES (1,0,'iphone-15-pro-max','iPhone 15 Pro Max','iPhone flagship cao cấp, màn hình đẹp, hiệu năng mạnh, camera tốt.',25990000,32990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',1,1,1,'https://cdn2.cellphones.com.vn/x/media/catalog/product/v/n/vn_iphone_15_pro_white_titanium_pdp_image_position-1a_white_titanium_color.jpg','8GB','256GB'),(2,0,'iphone-14-pro-max','iPhone 14 Pro Max','iPhone cao cấp với Dynamic Island, camera tốt, pin ổn.',21990000,28990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',1,1,1,'https://cdn.tgdd.vn/Products/Images/42/289663/iPhone-14-plus-thumb-den-600x600.jpg','6GB','256GB'),(3,0,'iphone-13','iPhone 13','iPhone phổ biến, hiệu năng ổn định, camera đẹp, phù hợp dùng lâu dài.',11990000,17990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',1,1,1,'https://cdn.tgdd.vn/Products/Images/42/223602/iphone-13-xanh-la-thumb-new-600x600.jpg','4GB','128GB'),(4,0,'samsung-galaxy-s24-ultra','Samsung Galaxy S24 Ultra','Flagship Samsung cao cấp, màn hình lớn, camera zoom tốt, hỗ trợ bút S Pen.',26990000,33990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',2,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2024/01/samsung-galaxy-s24-ultra-xam-titan.jpg.webp','12GB','256GB'),(5,0,'samsung-galaxy-s23-ultra','Samsung Galaxy S23 Ultra','Flagship Android mạnh, camera 200MP, pin tốt, thiết kế cao cấp.',19990000,29990000,'GOOD',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',2,1,1,'https://m.media-amazon.com/images/I/31L0aIATrwL._SL500_.jpg','12GB','256GB'),(6,0,'samsung-galaxy-z-flip5','Samsung Galaxy Z Flip5','Điện thoại gập nhỏ gọn, màn hình phụ tiện lợi, thiết kế thời trang.',15990000,25990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',2,1,1,'https://cdn11.dienmaycholon.vn/filewebdmclnew/DMCL21/Picture/Apro/Apro_product_33078/samsung-galaxy-_main_367.png','8GB','256GB'),(7,0,'xiaomi-14-ultra','Xiaomi 14 Ultra','Flagship Xiaomi mạnh, camera cao cấp, sạc nhanh, màn hình đẹp.',22990000,32990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',7,1,1,'https://cdn.tgdd.vn/Products/Images/42/313889/xiaomi-14-ultra-black-thumbnew-600x600.jpg','16GB','512GB'),(8,0,'xiaomi-13t-pro','Xiaomi 13T Pro','Máy hiệu năng cao, sạc nhanh, camera Leica, giá tốt.',10990000,16990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',7,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2023/09/xiaomi-13t-pro-xanh-duong.jpg.webp','12GB','512GB'),(9,0,'oppo-find-x7-ultra','Oppo Find X7 Ultra','Flagship Oppo với camera mạnh, màn hình đẹp, sạc nhanh.',18990000,26990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',134,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2024/01/oppo-find-x7-ultra-xanh.jpg.webp','16GB','512GB'),(10,0,'oppo-reno11-pro','Oppo Reno11 Pro','Thiết kế đẹp, camera chân dung tốt, phù hợp người dùng trẻ.',8990000,13990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',134,1,1,'https://cdn.tgdd.vn/Products/Images/42/314210/oppo-reno-11-pro-xam-1-1-750x500.jpg','12GB','256GB'),(11,0,'vivo-x100-pro','Vivo X100 Pro','Camera Zeiss nổi bật, hiệu năng cao, pin tốt.',17990000,24990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',9,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2023/11/vivo-x100-pro-5g-xanh.jpg.webp','16GB','512GB'),(12,0,'vivo-v30','Vivo V30','Điện thoại mỏng nhẹ, camera selfie tốt, màn hình đẹp.',7990000,11990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',9,1,1,'https://cdn.media.amplience.net/i/xcite/656548-03?img404=default&w=2048&qlt=75&fmt=auto','12GB','256GB'),(13,0,'google-pixel-8-pro','Google Pixel 8 Pro','Pixel flagship, camera xử lý ảnh tốt, Android gốc mượt.',17990000,25990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',145,1,1,'https://storage.googleapis.com/gweb-uniblog-publish-prod/original_images/Pixel_8_in_Obsidian.jpg','12GB','256GB'),(14,0,'google-pixel-7-pro','Google Pixel 7 Pro','Camera đẹp, Android gốc, trải nghiệm phần mềm tốt.',10990000,17990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',145,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2023/03/google-pixel-7-pro-xam.jpg.webp','12GB','128GB'),(15,0,'oneplus-12','OnePlus 12','Hiệu năng mạnh, sạc nhanh, màn hình đẹp, OxygenOS mượt.',16990000,23990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',140,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2023/12/oneplus-12-xanh.jpg.webp','16GB','512GB'),(16,0,'realme-gt5-pro','Realme GT5 Pro','Hiệu năng flagship, pin tốt, sạc nhanh, giá cạnh tranh.',12990000,18990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',136,1,1,'https://cdn2.cellphones.com.vn/insecure/rs:fill:0:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/r/e/realme-gt-5_1__1.png','16GB','512GB'),(17,0,'honor-magic6-pro','Honor Magic6 Pro','Flagship Honor, camera mạnh, pin lớn, thiết kế cao cấp.',18990000,26990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',143,1,1,'https://www.hihonor.com/content/dam/honor/global/product-list/smartphone/honor-magic6-pro/honor-magic6-pro-green.png','12GB','512GB'),(18,0,'huawei-p60-pro','Huawei P60 Pro','Camera cao cấp, thiết kế đẹp, màn hình tốt.',13990000,21990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',141,1,1,'https://consumer.huawei.com/dam/content/dam/huawei-cbg-site/common/mkt/pdp/phones/p60-pro/images/design/huawei-p60-pro-id-2x.webp','8GB','256GB'),(19,0,'sony-xperia-1-v','Sony Xperia 1 V','Điện thoại Sony cao cấp, màn hình 4K, camera thiên về chỉnh tay.',15990000,24990000,'GOOD',6,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',6,1,1,'https://cdn2.cellphones.com.vn/insecure/rs:fill:0:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/s/o/sony-xperia-1-v_3_.png','12GB','256GB'),(20,0,'asus-rog-phone-8-pro','Asus ROG Phone 8 Pro','Gaming phone mạnh, màn hình mượt, pin tốt, hiệu năng cao.',19990000,28990000,'LIKE_NEW',12,NULL,0,'2026-05-31 12:49:54.000000','2026-05-31 12:49:54.000000',5,1,1,'https://cdn.mobilecity.vn/mobilecity-vn/images/2024/01/asus-rog-phone-8-pro-dai-dien.jpg.webp','16GB','512GB');
/*!40000 ALTER TABLE `products_product` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-02 15:05:12
