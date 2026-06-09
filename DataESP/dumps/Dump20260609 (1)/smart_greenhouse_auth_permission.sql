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
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add user',4,'add_user'),(14,'Can change user',4,'change_user'),(15,'Can delete user',4,'delete_user'),(16,'Can view user',4,'view_user'),(17,'Can add content type',5,'add_contenttype'),(18,'Can change content type',5,'change_contenttype'),(19,'Can delete content type',5,'delete_contenttype'),(20,'Can view content type',5,'view_contenttype'),(21,'Can add session',6,'add_session'),(22,'Can change session',6,'change_session'),(23,'Can delete session',6,'delete_session'),(24,'Can view session',6,'view_session'),(25,'Can add device state',7,'add_devicestate'),(26,'Can change device state',7,'change_devicestate'),(27,'Can delete device state',7,'delete_devicestate'),(28,'Can view device state',7,'view_devicestate'),(29,'Can add sensor data',8,'add_sensordata'),(30,'Can change sensor data',8,'change_sensordata'),(31,'Can delete sensor data',8,'delete_sensordata'),(32,'Can view sensor data',8,'view_sensordata'),(33,'Can add alert',9,'add_alert'),(34,'Can change alert',9,'change_alert'),(35,'Can delete alert',9,'delete_alert'),(36,'Can view alert',9,'view_alert'),(37,'Can add device command',10,'add_devicecommand'),(38,'Can change device command',10,'change_devicecommand'),(39,'Can delete device command',10,'delete_devicecommand'),(40,'Can view device command',10,'view_devicecommand'),(41,'Can add Control state',11,'add_controlstate'),(42,'Can change Control state',11,'change_controlstate'),(43,'Can delete Control state',11,'delete_controlstate'),(44,'Can view Control state',11,'view_controlstate'),(45,'Can add Control profile',12,'add_controlprofile'),(46,'Can change Control profile',12,'change_controlprofile'),(47,'Can delete Control profile',12,'delete_controlprofile'),(48,'Can view Control profile',12,'view_controlprofile'),(49,'Can add estimation cycle',13,'add_estimationcycle'),(50,'Can change estimation cycle',13,'change_estimationcycle'),(51,'Can delete estimation cycle',13,'delete_estimationcycle'),(52,'Can view estimation cycle',13,'view_estimationcycle'),(53,'Can add ampc recommendation',14,'add_ampcrecommendation'),(54,'Can change ampc recommendation',14,'change_ampcrecommendation'),(55,'Can delete ampc recommendation',14,'delete_ampcrecommendation'),(56,'Can view ampc recommendation',14,'view_ampcrecommendation'),(57,'Can add experiment run',15,'add_experimentrun'),(58,'Can change experiment run',15,'change_experimentrun'),(59,'Can delete experiment run',15,'delete_experimentrun'),(60,'Can view experiment run',15,'view_experimentrun'),(61,'Can add experiment config',16,'add_experimentconfig'),(62,'Can change experiment config',16,'change_experimentconfig'),(63,'Can delete experiment config',16,'delete_experimentconfig'),(64,'Can view experiment config',16,'view_experimentconfig'),(65,'Can add evaluation summary',17,'add_evaluationsummary'),(66,'Can change evaluation summary',17,'change_evaluationsummary'),(67,'Can delete evaluation summary',17,'delete_evaluationsummary'),(68,'Can view evaluation summary',17,'view_evaluationsummary'),(69,'Can add greenhouse control profile',18,'add_greenhousecontrolprofile'),(70,'Can change greenhouse control profile',18,'change_greenhousecontrolprofile'),(71,'Can delete greenhouse control profile',18,'delete_greenhousecontrolprofile'),(72,'Can view greenhouse control profile',18,'view_greenhousecontrolprofile'),(73,'Can add AMPC scheduler state',19,'add_ampcschedulerstate'),(74,'Can change AMPC scheduler state',19,'change_ampcschedulerstate'),(75,'Can delete AMPC scheduler state',19,'delete_ampcschedulerstate'),(76,'Can view AMPC scheduler state',19,'view_ampcschedulerstate'),(77,'Can add greenhouse',20,'add_greenhouse'),(78,'Can change greenhouse',20,'change_greenhouse'),(79,'Can delete greenhouse',20,'delete_greenhouse'),(80,'Can view greenhouse',20,'view_greenhouse');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
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

-- Dump completed on 2026-06-09 19:25:09
