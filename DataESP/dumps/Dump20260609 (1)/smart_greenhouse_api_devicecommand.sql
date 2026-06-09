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
-- Table structure for table `api_devicecommand`
--

DROP TABLE IF EXISTS `api_devicecommand`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_devicecommand` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `command` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `value` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload` json NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acked_at` datetime(6) DEFAULT NULL,
  `device_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'legacy',
  PRIMARY KEY (`id`),
  KEY `cmd_status_created_idx` (`status`,`created_at`),
  KEY `api_devicecommand_device_code_idx` (`device_code`)
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `api_devicecommand`
--

LOCK TABLES `api_devicecommand` WRITE;
/*!40000 ALTER TABLE `api_devicecommand` DISABLE KEYS */;
INSERT INTO `api_devicecommand` VALUES (1,'2026-06-09 08:50:12.412517','2026-06-09 08:50:12.490159','set_power','off','{}','ack','2026-06-09 08:50:12.490159','pump'),(2,'2026-06-09 08:50:44.167903','2026-06-09 08:50:44.342308','set_power','on','{}','ack','2026-06-09 08:50:44.342308','light'),(3,'2026-06-09 08:52:51.101882','2026-06-09 08:52:51.197551','set_power','off','{}','ack','2026-06-09 08:52:51.197551','light'),(4,'2026-06-09 11:42:41.092748','2026-06-09 11:42:41.239467','set_power','on','{}','ack','2026-06-09 11:42:41.239467','fan'),(5,'2026-06-09 11:42:43.337901','2026-06-09 11:42:43.482818','set_power','off','{}','ack','2026-06-09 11:42:43.482818','fan'),(6,'2026-06-09 11:42:45.390549','2026-06-09 11:42:45.649199','set_power','on','{}','ack','2026-06-09 11:42:45.640920','light'),(7,'2026-06-09 11:42:47.674937','2026-06-09 11:42:47.893272','set_power','off','{}','ack','2026-06-09 11:42:47.892159','light'),(8,'2026-06-09 11:42:50.232783','2026-06-09 11:42:50.358910','set_power','on','{}','ack','2026-06-09 11:42:50.358910','pump'),(9,'2026-06-09 11:42:52.644749','2026-06-09 11:42:52.844973','set_power','off','{}','ack','2026-06-09 11:42:52.844973','pump'),(10,'2026-06-09 11:42:54.796327','2026-06-09 11:42:54.954082','set_power','on','{}','ack','2026-06-09 11:42:54.954082','mist'),(11,'2026-06-09 11:42:59.767176','2026-06-09 11:42:59.880285','set_power','off','{}','ack','2026-06-09 11:42:59.880285','mist'),(12,'2026-06-09 11:43:02.310665','2026-06-09 11:43:02.536226','set_power','on','{}','ack','2026-06-09 11:43:02.536226','fan'),(13,'2026-06-09 11:43:03.499478','2026-06-09 11:43:03.652322','set_power','on','{}','ack','2026-06-09 11:43:03.652322','light'),(14,'2026-06-09 11:43:04.790520','2026-06-09 11:43:04.997072','set_power','on','{}','ack','2026-06-09 11:43:04.997072','pump'),(15,'2026-06-09 11:43:06.081070','2026-06-09 11:43:06.222922','set_power','on','{}','ack','2026-06-09 11:43:06.222922','mist'),(16,'2026-06-09 11:43:08.911538','2026-06-09 11:43:09.189057','set_power','off','{}','ack','2026-06-09 11:43:09.189057','mist'),(17,'2026-06-09 11:43:10.498524','2026-06-09 11:43:10.619974','set_power','off','{}','ack','2026-06-09 11:43:10.619974','pump'),(18,'2026-06-09 11:43:11.556404','2026-06-09 11:43:11.759174','set_power','off','{}','ack','2026-06-09 11:43:11.759174','light'),(19,'2026-06-09 11:43:12.804175','2026-06-09 11:43:12.995553','set_power','off','{}','ack','2026-06-09 11:43:12.995553','fan'),(20,'2026-06-09 11:43:31.650904','2026-06-09 11:43:31.826717','set_power','on','{}','ack','2026-06-09 11:43:31.826717','fan'),(21,'2026-06-09 11:44:58.869515','2026-06-09 11:44:59.185034','set_power','off','{}','ack','2026-06-09 11:44:59.185034','fan'),(22,'2026-06-09 11:46:58.271272','2026-06-09 11:46:58.459855','set_power','on','{}','ack','2026-06-09 11:46:58.459855','pump'),(23,'2026-06-09 11:47:00.460048','2026-06-09 11:47:00.840998','set_power','off','{}','ack','2026-06-09 11:47:00.840998','pump'),(24,'2026-06-09 11:47:30.670002','2026-06-09 11:47:30.835396','set_power','on','{}','ack','2026-06-09 11:47:30.835396','fan'),(25,'2026-06-09 11:47:41.300736','2026-06-09 11:47:41.458574','set_power','on','{}','ack','2026-06-09 11:47:41.458574','light'),(26,'2026-06-09 11:47:47.819257','2026-06-09 11:47:47.924324','set_power','on','{}','ack','2026-06-09 11:47:47.924324','pump'),(27,'2026-06-09 11:47:55.737300','2026-06-09 11:47:55.908219','set_power','on','{}','ack','2026-06-09 11:47:55.908219','mist'),(28,'2026-06-09 11:48:11.051100','2026-06-09 11:48:11.166360','set_power','off','{}','ack','2026-06-09 11:48:11.166360','mist'),(29,'2026-06-09 11:48:12.059440','2026-06-09 11:48:12.180842','set_power','off','{}','ack','2026-06-09 11:48:12.180842','pump'),(30,'2026-06-09 11:48:13.245504','2026-06-09 11:48:13.405472','set_power','off','{}','ack','2026-06-09 11:48:13.405472','light'),(31,'2026-06-09 11:48:14.305800','2026-06-09 11:48:14.433772','set_power','off','{}','ack','2026-06-09 11:48:14.433772','fan'),(32,'2026-06-09 11:50:53.202183','2026-06-09 11:50:53.357949','set_power','on','{}','ack','2026-06-09 11:50:53.357949','pump'),(33,'2026-06-09 11:50:55.002471','2026-06-09 11:50:55.189856','set_power','off','{}','ack','2026-06-09 11:50:55.189856','pump'),(34,'2026-06-09 12:12:07.189906','2026-06-09 12:12:07.189906','set_power','on','{\"source\": \"mpc\", \"duration\": 7.729, \"skip_reason\": \"pump_already_on\", \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1221}','skipped','2026-06-09 12:12:07.189906','pump'),(35,'2026-06-09 12:12:42.043701','2026-06-09 12:12:42.082844','set_power','on','{\"source\": \"mpc\", \"duration\": 4.148, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1223}','failed','2026-06-09 12:12:42.082844','pump'),(36,'2026-06-09 12:13:34.408330','2026-06-09 12:13:34.559783','set_power','on','{\"source\": \"mpc\", \"duration\": 2.226, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1225}','failed','2026-06-09 12:13:34.559783','pump'),(37,'2026-06-09 12:14:26.652634','2026-06-09 12:14:26.803058','set_power','on','{\"source\": \"mpc\", \"duration\": 1.195, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1227}','failed','2026-06-09 12:14:26.803058','pump'),(38,'2026-06-09 12:15:20.138874','2026-06-09 12:15:20.543983','set_power','on','{\"source\": \"mpc\", \"duration\": 0.641, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1229}','failed','2026-06-09 12:15:20.543983','pump'),(39,'2026-06-09 12:16:12.181923','2026-06-09 12:16:12.464045','set_power','on','{\"source\": \"mpc\", \"duration\": 0.344, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1231}','failed','2026-06-09 12:16:12.464045','pump'),(40,'2026-06-09 12:17:04.555065','2026-06-09 12:17:05.101814','set_power','on','{\"source\": \"mpc\", \"duration\": 0.185, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1233}','failed','2026-06-09 12:17:05.101814','pump'),(41,'2026-06-09 12:17:58.746150','2026-06-09 12:17:58.868800','set_power','on','{\"source\": \"mpc\", \"duration\": 0.099, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1235}','failed','2026-06-09 12:17:58.867691','pump'),(42,'2026-06-09 12:18:51.273418','2026-06-09 12:18:51.800864','set_power','on','{\"source\": \"mpc\", \"duration\": 0.053, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1237}','failed','2026-06-09 12:18:51.800864','pump'),(43,'2026-06-09 12:19:43.381347','2026-06-09 12:19:44.030421','set_power','on','{\"source\": \"mpc\", \"duration\": 0.029, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1239}','failed','2026-06-09 12:19:44.030421','pump'),(44,'2026-06-09 12:20:35.519931','2026-06-09 12:20:35.844757','set_power','on','{\"source\": \"mpc\", \"duration\": 0.015, \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1241}','failed','2026-06-09 12:20:35.844757','pump'),(45,'2026-06-09 12:21:29.855581','2026-06-09 12:21:29.855581','set_power','off','{\"source\": \"mpc\", \"duration\": 0, \"skip_reason\": \"pump_already_off\", \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1243}','skipped','2026-06-09 12:21:29.855581','pump'),(46,'2026-06-09 12:22:21.681396','2026-06-09 12:22:21.681396','set_power','off','{\"source\": \"mpc\", \"duration\": 0, \"skip_reason\": \"pump_already_off\", \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1245}','skipped','2026-06-09 12:22:21.681396','pump'),(47,'2026-06-09 12:23:13.524698','2026-06-09 12:23:13.524698','set_power','off','{\"source\": \"mpc\", \"duration\": 0, \"skip_reason\": \"pump_already_off\", \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1247}','skipped','2026-06-09 12:23:13.524698','pump'),(48,'2026-06-09 12:24:05.372210','2026-06-09 12:24:05.372210','set_power','off','{\"source\": \"mpc\", \"duration\": 0, \"skip_reason\": \"pump_already_off\", \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1249}','skipped','2026-06-09 12:24:05.372210','pump'),(49,'2026-06-09 12:24:57.283578','2026-06-09 12:24:57.283578','set_power','off','{\"source\": \"mpc\", \"duration\": 0, \"skip_reason\": \"pump_already_off\", \"step_seconds\": 50, \"safety_status\": \"safe\", \"recommendation_id\": 1251}','skipped','2026-06-09 12:24:57.283578','pump');
/*!40000 ALTER TABLE `api_devicecommand` ENABLE KEYS */;
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

-- Dump completed on 2026-06-09 19:25:11
