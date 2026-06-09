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
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=42 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-06-09 08:28:40.201370'),(2,'auth','0001_initial','2026-06-09 08:28:40.625040'),(3,'admin','0001_initial','2026-06-09 08:28:40.776636'),(4,'admin','0002_logentry_remove_auto_add','2026-06-09 08:28:40.786378'),(5,'admin','0003_logentry_add_action_flag_choices','2026-06-09 08:28:40.793190'),(6,'api','0001_initial','2026-06-09 08:28:41.340151'),(7,'api','0002_sensorcurrent','2026-06-09 08:28:41.444694'),(8,'api','0003_controlstate','2026-06-09 08:28:41.469596'),(9,'api','0004_delete_controlstate_and_more','2026-06-09 08:28:41.642831'),(10,'api','0005_controlstate','2026-06-09 08:28:41.669745'),(11,'api','0006_controlprofile_alter_device_device_type_and_more','2026-06-09 08:28:42.127981'),(12,'api','0007_align_estimationcycle_with_pipeline','2026-06-09 08:28:43.018744'),(13,'api','0008_green_house_server_cutover','2026-06-09 08:28:43.674087'),(14,'api','0009_ampc_scheduler_state','2026-06-09 08:28:43.727984'),(15,'api','0010_add_fao56_control_profile_config','2026-06-09 08:28:44.400809'),(16,'api','0011_scope_device_code_per_greenhouse','2026-06-09 08:28:44.540165'),(17,'api','0012_remove_greenhouse_device','2026-06-09 08:28:45.058561'),(18,'api','0013_cleanup_legacy_ampc_kalman_fields','2026-06-09 08:29:19.758971'),(19,'api','0014_restore_greenhouse_profile_scope','2026-06-09 08:29:19.939602'),(20,'api','0015_seed_user_greenhouse_configs','2026-06-09 08:29:19.964262'),(21,'api','0016_remove_mpc_adaptive_rls_fields','2026-06-09 08:29:20.225050'),(22,'api','0017_repair_devicestate_device_code','2026-06-09 08:29:20.248654'),(23,'api','0018_repair_devicecommand_device_code','2026-06-09 08:29:20.269620'),(24,'api','0019_set_pump_flow_default_to_001','2026-06-09 08:29:20.291092'),(25,'contenttypes','0002_remove_content_type_name','2026-06-09 08:29:20.533830'),(26,'auth','0002_alter_permission_name_max_length','2026-06-09 08:29:20.600146'),(27,'auth','0003_alter_user_email_max_length','2026-06-09 08:29:20.619715'),(28,'auth','0004_alter_user_username_opts','2026-06-09 08:29:20.631235'),(29,'auth','0005_alter_user_last_login_null','2026-06-09 08:29:20.685130'),(30,'auth','0006_require_contenttypes_0002','2026-06-09 08:29:20.690162'),(31,'auth','0007_alter_validators_add_error_messages','2026-06-09 08:29:20.698788'),(32,'auth','0008_alter_user_username_max_length','2026-06-09 08:29:20.745721'),(33,'auth','0009_alter_user_last_name_max_length','2026-06-09 08:29:20.808380'),(34,'auth','0010_alter_group_name_max_length','2026-06-09 08:29:20.830712'),(35,'auth','0011_update_proxy_permissions','2026-06-09 08:29:20.843595'),(36,'auth','0012_alter_user_first_name_max_length','2026-06-09 08:29:20.897114'),(37,'sessions','0001_initial','2026-06-09 08:29:20.933488'),(38,'api','0020_add_esp32_thresholds','2026-06-09 08:47:58.262759'),(39,'api','0020_remove_legacy_experiments_and_daily_cap','2026-06-09 10:10:29.018642'),(40,'api','0021_merge_esp32_thresholds_legacy_cleanup','2026-06-09 10:10:29.021018'),(41,'api','0022_devicecommand_skipped_status','2026-06-09 10:10:29.022450');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
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

-- Dump completed on 2026-06-09 17:36:02
