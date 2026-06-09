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

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'd9697354-1ee8-11f1-b216-3c219c7bc94b:1-136970';

--
-- Table structure for table `api_ampcschedulerstate`
--

DROP TABLE IF EXISTS `api_ampcschedulerstate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_ampcschedulerstate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `singleton_key` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `interval_seconds` int unsigned NOT NULL,
  `is_executing` tinyint(1) NOT NULL,
  `last_started_at` datetime(6) DEFAULT NULL,
  `last_stopped_at` datetime(6) DEFAULT NULL,
  `last_run_at` datetime(6) DEFAULT NULL,
  `next_run_at` datetime(6) DEFAULT NULL,
  `last_status` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_error` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `greenhouse_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `singleton_key` (`singleton_key`),
  KEY `api_ampcschedulerstate_greenhouse_id_061fe682` (`greenhouse_id`),
  CONSTRAINT `api_ampcschedulerstate_chk_1` CHECK ((`interval_seconds` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `api_ampcschedulerstate`
--

LOCK TABLES `api_ampcschedulerstate` WRITE;
/*!40000 ALTER TABLE `api_ampcschedulerstate` DISABLE KEYS */;
INSERT INTO `api_ampcschedulerstate` VALUES (1,'2026-06-09 08:43:11.849122','2026-06-09 10:34:14.227694','main',1,180,0,'2026-06-09 10:24:49.637637','2026-06-09 10:24:47.010318','2026-06-09 10:34:14.227694','2026-06-09 10:37:14.227694','3/4 unsafe','stale_sample; stale_sample; missing_estimation',NULL);
/*!40000 ALTER TABLE `api_ampcschedulerstate` ENABLE KEYS */;
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

-- Dump completed on 2026-06-09 17:36:03
