-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: smart_greenhouse
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

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'd9697354-1ee8-11f1-b216-3c219c7bc94b:1-141954';

--
-- Table structure for table `api_devicestate`
--

DROP TABLE IF EXISTS `api_devicestate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_devicestate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `is_on` tinyint(1) NOT NULL,
  `desired_on` tinyint(1) NOT NULL,
  `last_command` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_value` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `extra` json NOT NULL,
  `device_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_devicestate_device_code` (`device_code`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `api_devicestate`
--

LOCK TABLES `api_devicestate` WRITE;
/*!40000 ALTER TABLE `api_devicestate` DISABLE KEYS */;
INSERT INTO `api_devicestate` VALUES (1,'2026-06-09 08:31:03.822136','2026-06-09 08:31:03.822136',0,0,'','','{}','esp32-main'),(2,'2026-06-09 08:31:03.823135','2026-06-09 12:25:07.356071',0,0,'telemetry_sync','off','{}','fan'),(3,'2026-06-09 08:31:03.823135','2026-06-09 12:25:07.367459',0,0,'telemetry_sync','off','{}','pump'),(4,'2026-06-09 08:31:03.823135','2026-06-09 12:25:07.372074',0,0,'telemetry_sync','off','{}','light'),(5,'2026-06-09 08:31:03.823135','2026-06-09 12:25:07.372074',0,0,'telemetry_sync','off','{}','mist');
/*!40000 ALTER TABLE `api_devicestate` ENABLE KEYS */;
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

-- Dump completed on 2026-06-09 19:25:10
