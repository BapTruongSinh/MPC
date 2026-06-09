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
-- Table structure for table `greenhouse_control_profiles`
--

DROP TABLE IF EXISTS `greenhouse_control_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `greenhouse_control_profiles` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `crop_name` varchar(100) NOT NULL DEFAULT 'Default crop',
  `crop_kc` double NOT NULL DEFAULT '1',
  `target_low` double NOT NULL DEFAULT '55',
  `target_high` double NOT NULL DEFAULT '65',
  `step_seconds` int unsigned NOT NULL DEFAULT '300',
  `horizon_steps` int unsigned NOT NULL DEFAULT '12',
  `pump_min_seconds` double NOT NULL DEFAULT '0',
  `pump_max_seconds` double NOT NULL DEFAULT '300',
  `cost_band_violation` double NOT NULL DEFAULT '10',
  `cost_water_use` double NOT NULL DEFAULT '0.2',
  `cost_switching` double NOT NULL DEFAULT '0.5',
  `cost_terminal_band_violation` double NOT NULL DEFAULT '20',
  `safety_stale_after_seconds` int unsigned NOT NULL DEFAULT '600',
  `actuator_enabled` tinyint(1) NOT NULL DEFAULT '0',
  `actuator_url` varchar(500) DEFAULT NULL,
  `actuator_bearer_token_env` varchar(120) DEFAULT NULL,
  `actuator_timeout_seconds` double NOT NULL DEFAULT '5',
  `depletion_fraction_p` double NOT NULL,
  `irrigation_area_m2` double NOT NULL,
  `latitude` double NOT NULL,
  `longitude` double NOT NULL,
  `pump_efficiency` double NOT NULL,
  `pump_flow_lps` double NOT NULL,
  `root_depth_m` double NOT NULL,
  `soil_type` varchar(32) NOT NULL,
  `theta_fc` double NOT NULL,
  `theta_wp` double NOT NULL,
  `singleton_key` varchar(20) NOT NULL,
  `greenhouse_id` bigint DEFAULT NULL,
  `thresh_hum_fan_off` double NOT NULL,
  `thresh_hum_fan_on` double NOT NULL,
  `thresh_hum_mist_off` double NOT NULL,
  `thresh_hum_mist_on` double NOT NULL,
  `thresh_light_off_ldr` int NOT NULL,
  `thresh_light_on_ldr` int NOT NULL,
  `thresh_soil_pump_off` double NOT NULL,
  `thresh_soil_pump_on` double NOT NULL,
  `thresh_temp_fan_off` double NOT NULL,
  `thresh_temp_fan_on` double NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `greenhouse_control_profiles_singleton_key_7977f734_uniq` (`singleton_key`),
  UNIQUE KEY `uq_greenhouse_control_profile_greenhouse` (`greenhouse_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `greenhouse_control_profiles`
--

LOCK TABLES `greenhouse_control_profiles` WRITE;
/*!40000 ALTER TABLE `greenhouse_control_profiles` DISABLE KEYS */;
INSERT INTO `greenhouse_control_profiles` VALUES (1,'2026-06-09 08:29:19.958262','2026-06-09 08:29:19.958262','Default crop',1,55,65,300,12,0,300,10,0.2,0.5,20,600,0,NULL,NULL,5,0.5,0.25,16.0471,108.2068,0.8,0.001,0.3,'loam',0.32,0.15,'gh-1',1,70,80,65,55,40,20,40,35,30,32),(2,'2026-06-09 08:38:58.813089','2026-06-09 08:38:58.813089','Default crop',1,55,65,300,12,0,300,10,0.2,0.5,20,600,0,NULL,NULL,5,0.5,0.25,16.0471,108.2068,0.8,0.001,0.3,'loam',0.32,0.15,'gh-2',2,70,80,65,55,40,20,40,35,30,32),(3,'2026-06-09 08:39:53.818973','2026-06-09 08:39:53.818973','Default crop',1,55,65,300,12,0,300,10,0.2,0.5,20,600,0,NULL,NULL,5,0.5,0.25,16.0471,108.2068,0.8,0.001,0.3,'loam',0.32,0.15,'gh-3',3,70,80,65,55,40,20,40,35,30,32),(4,'2026-06-09 08:43:06.704814','2026-06-09 10:12:50.758493','Default crop',1,45,55,180,12,0,180,10,0.2,0.5,20,600,0,NULL,NULL,5,0.5,0.25,16.0471,108.2068,0.8,0.001,0.3,'loam',0.32,0.15,'gh-4',4,70,80,65,55,40,20,40,35,30,32);
/*!40000 ALTER TABLE `greenhouse_control_profiles` ENABLE KEYS */;
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
