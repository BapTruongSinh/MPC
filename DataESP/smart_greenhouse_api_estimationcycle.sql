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
-- Table structure for table `api_estimationcycle`
--

DROP TABLE IF EXISTS `api_estimationcycle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_estimationcycle` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `sample_ts` datetime(6) NOT NULL,
  `cycle_index` int unsigned NOT NULL,
  `validation_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `validation_reason` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `preprocess_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cycle_status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `adaptive_status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `raw_soil_moisture` double DEFAULT NULL,
  `raw_temperature` double DEFAULT NULL,
  `raw_humidity` double DEFAULT NULL,
  `raw_light` double DEFAULT NULL,
  `raw_drip` double DEFAULT NULL,
  `raw_mist` double DEFAULT NULL,
  `raw_fan` double DEFAULT NULL,
  `arx_predicted` double DEFAULT NULL,
  `kf_x_prior` double DEFAULT NULL,
  `kf_P_prior` double DEFAULT NULL,
  `kf_innovation` double DEFAULT NULL,
  `kf_R` double DEFAULT NULL,
  `kf_K` double DEFAULT NULL,
  `kf_x_posterior` double DEFAULT NULL,
  `kf_P_posterior` double DEFAULT NULL,
  `latency_ms` double DEFAULT NULL,
  `error_message` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `greenhouse_id` int DEFAULT NULL,
  `ingest_dedupe_key` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slice_type` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `est_sample_id_idx` (`sample_ts`,`id`),
  KEY `est_status_ts_idx` (`cycle_status`,`sample_ts`),
  KEY `api_estimationcycle_sample_ts_0ac1c1ec` (`sample_ts`),
  KEY `api_estimationcycle_cycle_index_5a22920c` (`cycle_index`),
  KEY `api_estimationcycle_greenhouse_id_906890b4` (`greenhouse_id`),
  CONSTRAINT `api_estimationcycle_chk_1` CHECK ((`cycle_index` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `api_estimationcycle`
--

LOCK TABLES `api_estimationcycle` WRITE;
/*!40000 ALTER TABLE `api_estimationcycle` DISABLE KEYS */;
INSERT INTO `api_estimationcycle` VALUES (1,'2026-06-09 10:13:33.227001','2026-06-09 10:13:33.227001','2026-06-09 08:38:53.791817',0,'valid','','valid','ok','R_updated',0,28.8,47.8,NULL,1,0,0,NULL,0,13,0,0.25,0.9811320754716981,0,0.24528301886792447,0.032599782571196556,'',1,'live|sensor:1|2026-06-09T15:38:53.791817+07:00','online','live'),(2,'2026-06-09 10:13:34.639604','2026-06-09 10:13:34.639604','2026-06-09 08:39:48.787108',0,'valid','','valid','ok','R_updated',0,28.8,47.7,NULL,1,0,0,NULL,0,13,0,0.25,0.9811320754716981,0,0.24528301886792447,0.0271000899374485,'',2,'live|sensor:2|2026-06-09T15:39:48.787108+07:00','online','live'),(3,'2026-06-09 10:13:35.786339','2026-06-09 10:13:35.786339','2026-06-09 09:15:00.000000',0,'valid','','valid','ok','R_updated',26.21083333333333,28.93666666666669,56.031666666666645,NULL,0,0,0,NULL,26.21083333333333,13,0,0.25,0.9811320754716981,26.21083333333333,0.24528301886792447,0.021399930119514465,'',3,'window|sensor:3|300|2026-06-09T16:10:00+07:00|2026-06-09T16:15:00+07:00','online','live_window'),(4,'2026-06-09 10:13:35.802195','2026-06-09 10:13:35.802195','2026-06-09 09:20:00.000000',1,'valid','','valid','ok','R_updated',26.27,28.800000000000004,56.44,NULL,0,0,0,NULL,26.21083333333333,12.245283018867925,0.0591666666666697,0.25,0.979992449981125,26.268816219957216,0.24499811249528064,0.017700018361210823,'',3,'window|sensor:3|300|2026-06-09T16:15:00+07:00|2026-06-09T16:20:00+07:00','online','live_window'),(5,'2026-06-09 10:16:42.628138','2026-06-09 10:16:42.628138','2026-06-09 10:15:00.000000',2,'valid','','valid','ok','R_updated',27.18155555555556,28.522222222222236,55.32666666666664,NULL,1,0.26666666666666666,0,NULL,26.268816219957216,12.244998112495281,0.9127393355983422,0.25,0.979991993776294,27.163293461248287,0.24499799844407408,0.015500001609325409,'',3,'window|sensor:3|300|2026-06-09T17:10:00+07:00|2026-06-09T17:15:00+07:00','online','live_window'),(6,'2026-06-09 10:22:50.303217','2026-06-09 10:22:50.303217','2026-06-09 10:20:00.000000',3,'valid','','valid','ok','R_updated',26.409999999999993,28.769999999999968,54.978333333333325,NULL,1,1,0,NULL,27.163293461248287,12.244997998444074,-0.753293461248294,0.25,0.979991993593666,26.4250719003985,0.24499799839841657,0.01910002902150154,'',3,'window|sensor:3|300|2026-06-09T17:15:00+07:00|2026-06-09T17:20:00+07:00','online','live_window'),(7,'2026-06-09 10:27:59.602062','2026-06-09 10:27:59.602062','2026-06-09 10:25:00.000000',4,'valid','','valid','ok','R_updated',26.19516666666666,28.803333333333306,54.955,NULL,1,1,0,NULL,26.4250719003985,12.244997998398416,-0.22990523373184146,0.25,0.9799919935935929,26.19976661205603,0.2449979983983976,0.02319994382560253,'',3,'window|sensor:3|300|2026-06-09T17:20:00+07:00|2026-06-09T17:25:00+07:00','online','live_window'),(8,'2026-06-09 10:31:03.975373','2026-06-09 10:31:03.975373','2026-06-09 10:30:00.000000',5,'valid','','valid','ok','R_updated',26.251730769230765,28.815384615384588,54.23653846153846,NULL,1,1,0,NULL,26.19976661205603,12.244997998398398,0.05196415717473357,0.25,0.9799919935935928,26.25069107004111,0.2449979983983986,0.015300000086426735,'',3,'window|sensor:3|300|2026-06-09T17:25:00+07:00|2026-06-09T17:30:00+07:00','online','live_window');
/*!40000 ALTER TABLE `api_estimationcycle` ENABLE KEYS */;
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

-- Dump completed on 2026-06-09 17:36:04
