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

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'd9697354-1ee8-11f1-b216-3c219c7bc94b:1-54423';

--
-- Table structure for table `products_brand`
--

DROP TABLE IF EXISTS `products_brand`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `products_brand` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_deleted` tinyint(1) NOT NULL,
  `slug` varchar(50) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `logo` varchar(100) DEFAULT NULL,
  `logo_svg` longtext,
  `description` longtext,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`),
  KEY `products_brand_is_deleted_ab9bca45` (`is_deleted`),
  KEY `products_br_slug_d4d839_idx` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=147 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `products_brand`
--

LOCK TABLES `products_brand` WRITE;
/*!40000 ALTER TABLE `products_brand` DISABLE KEYS */;
INSERT INTO `products_brand` VALUES (1,0,'apple','Apple','',NULL,NULL),(2,0,'samsung','Samsung','',NULL,NULL),(3,0,'dell','Dell','',NULL,NULL),(4,0,'lenovo','Lenovo','',NULL,NULL),(5,0,'asus','Asus','',NULL,NULL),(6,0,'sony','Sony','',NULL,NULL),(7,0,'xiaomi','Xiaomi','',NULL,NULL),(8,0,'acer','Acer','',NULL,NULL),(9,0,'vivo','Vivo','',NULL,NULL),(134,0,'oppo','Oppo','',NULL,NULL),(135,0,'infinix','Infinix','',NULL,NULL),(136,0,'realme','Realme','',NULL,NULL),(137,0,'motorola','Motorola','',NULL,NULL),(138,0,'tecno','Tecno','',NULL,NULL),(139,0,'zte','ZTE','',NULL,NULL),(140,0,'oneplus','OnePlus','',NULL,NULL),(141,0,'huawei','Huawei','',NULL,NULL),(142,0,'itel','Itel','',NULL,NULL),(143,0,'honor','Honor','',NULL,NULL),(144,0,'nokia','Nokia','',NULL,NULL),(145,0,'google','Google','',NULL,NULL),(146,0,'lg','LG','',NULL,NULL);
/*!40000 ALTER TABLE `products_brand` ENABLE KEYS */;
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

-- Dump completed on 2026-05-30  0:22:33
