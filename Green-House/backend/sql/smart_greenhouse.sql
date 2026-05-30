-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: May 09, 2026 at 12:22 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `smart_greenhouse`
--

-- --------------------------------------------------------

--
-- Table structure for table `api_alert`
--

CREATE TABLE `api_alert` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `level` varchar(20) NOT NULL,
  `title` varchar(100) NOT NULL,
  `message` varchar(255) NOT NULL,
  `is_read` tinyint(1) NOT NULL,
  `happened_at` datetime(6) NOT NULL,
  `device_id` bigint(20) DEFAULT NULL,
  `sensor_data_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_alert`
--

INSERT INTO `api_alert` (`id`, `created_at`, `updated_at`, `level`, `title`, `message`, `is_read`, `happened_at`, `device_id`, `sensor_data_id`) VALUES
(1, '2026-05-09 10:13:39.098879', '2026-05-09 10:13:39.098879', 'success', 'ESP32 Main online', 'ESP32 Main đã kết nối lại hệ thống.', 0, '2026-05-09 10:13:39.098879', 2, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `api_ampcrecommendation`
--

CREATE TABLE `api_ampcrecommendation` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `mode` varchar(10) NOT NULL,
  `pump_seconds` double NOT NULL,
  `step_seconds` int(10) UNSIGNED NOT NULL CHECK (`step_seconds` >= 0),
  `predicted_soil_moisture` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`predicted_soil_moisture`)),
  `target_band` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`target_band`)),
  `objective_cost` double NOT NULL,
  `safety_status` varchar(40) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `bias_correction` double NOT NULL,
  `bias_window_count` int(10) UNSIGNED NOT NULL CHECK (`bias_window_count` >= 0),
  `used_today_pump_seconds` double NOT NULL,
  `command_created` tinyint(1) NOT NULL,
  `actuator_status` varchar(30) NOT NULL,
  `config_snapshot` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`config_snapshot`)),
  `state_snapshot` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`state_snapshot`)),
  `device_command_id` bigint(20) DEFAULT NULL,
  `estimation_id` bigint(20) DEFAULT NULL,
  `sensor_data_id` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_ampcrecommendation`
--

INSERT INTO `api_ampcrecommendation` (`id`, `created_at`, `updated_at`, `mode`, `pump_seconds`, `step_seconds`, `predicted_soil_moisture`, `target_band`, `objective_cost`, `safety_status`, `reason`, `bias_correction`, `bias_window_count`, `used_today_pump_seconds`, `command_created`, `actuator_status`, `config_snapshot`, `state_snapshot`, `device_command_id`, `estimation_id`, `sensor_data_id`) VALUES
(1, '2026-05-09 10:13:39.147162', '2026-05-09 10:13:39.147162', 'MANUAL', 0, 300, '[]', '{\"low\": 55.0, \"high\": 65.0}', 0, 'model_error', 'history_too_short', 0, 0, 0, 0, 'disabled', '{\"crop_name\": \"Default crop\", \"crop_kc\": 1.0, \"target_low\": 55.0, \"target_high\": 65.0, \"step_seconds\": 300, \"horizon_steps\": 12, \"pump_min_seconds\": 0.0, \"pump_max_seconds\": 300.0, \"pump_grid_seconds\": 30.0, \"soft_daily_pump_cap_seconds\": 1800.0, \"weights\": {\"band\": 10.0, \"water\": 0.2, \"switch\": 0.5, \"daily\": 2.0, \"terminal\": 20.0}, \"adaptive_enabled\": true, \"adaptive_bias_window\": 12, \"adaptive_max_abs_bias\": 5.0, \"stale_after_seconds\": 600, \"actuator_enabled\": false}', '{\"sensor_data_id\": 1, \"estimation_id\": 1, \"timestamp\": \"2026-05-09T10:13:39.088835+00:00\", \"kf_x_posterior\": 61.5, \"raw_soil_moisture\": 61.5, \"temperature\": 28.5, \"humidity\": 67.2, \"light\": 5200.0, \"last_pump_seconds\": 0.0}', NULL, 1, 1);

-- --------------------------------------------------------

--
-- Table structure for table `api_controlprofile`
--

CREATE TABLE `api_controlprofile` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `singleton_key` varchar(20) NOT NULL,
  `crop_name` varchar(100) NOT NULL,
  `crop_kc` double NOT NULL,
  `target_low` double NOT NULL,
  `target_high` double NOT NULL,
  `step_seconds` int(10) UNSIGNED NOT NULL CHECK (`step_seconds` >= 0),
  `horizon_steps` int(10) UNSIGNED NOT NULL CHECK (`horizon_steps` >= 0),
  `pump_min_seconds` double NOT NULL,
  `pump_max_seconds` double NOT NULL,
  `pump_grid_seconds` double NOT NULL,
  `soft_daily_pump_cap_seconds` double NOT NULL,
  `weight_band` double NOT NULL,
  `weight_water` double NOT NULL,
  `weight_switch` double NOT NULL,
  `weight_daily` double NOT NULL,
  `weight_terminal` double NOT NULL,
  `adaptive_enabled` tinyint(1) NOT NULL,
  `adaptive_bias_window` int(10) UNSIGNED NOT NULL CHECK (`adaptive_bias_window` >= 0),
  `adaptive_max_abs_bias` double NOT NULL,
  `stale_after_seconds` int(10) UNSIGNED NOT NULL CHECK (`stale_after_seconds` >= 0),
  `actuator_enabled` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_controlprofile`
--

INSERT INTO `api_controlprofile` (`id`, `created_at`, `updated_at`, `singleton_key`, `crop_name`, `crop_kc`, `target_low`, `target_high`, `step_seconds`, `horizon_steps`, `pump_min_seconds`, `pump_max_seconds`, `pump_grid_seconds`, `soft_daily_pump_cap_seconds`, `weight_band`, `weight_water`, `weight_switch`, `weight_daily`, `weight_terminal`, `adaptive_enabled`, `adaptive_bias_window`, `adaptive_max_abs_bias`, `stale_after_seconds`, `actuator_enabled`) VALUES
(1, '2026-05-09 10:13:39.128814', '2026-05-09 10:13:39.134687', 'main', 'Default crop', 1, 55, 65, 300, 12, 0, 300, 30, 1800, 10, 0.2, 0.5, 2, 20, 1, 12, 5, 600, 0);

-- --------------------------------------------------------

--
-- Table structure for table `api_controlstate`
--

CREATE TABLE `api_controlstate` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `singleton_key` varchar(20) NOT NULL,
  `mode` varchar(10) NOT NULL,
  `manual_reason` varchar(255) NOT NULL,
  `manual_changed_at` datetime(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_controlstate`
--

INSERT INTO `api_controlstate` (`id`, `created_at`, `updated_at`, `singleton_key`, `mode`, `manual_reason`, `manual_changed_at`) VALUES
(1, '2026-05-09 10:13:39.101189', '2026-05-09 10:13:39.101189', 'main', 'MANUAL', '', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `api_device`
--

CREATE TABLE `api_device` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `name` varchar(100) NOT NULL,
  `code` varchar(50) NOT NULL,
  `device_type` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL,
  `firmware_version` varchar(50) NOT NULL,
  `api_token` varchar(64) NOT NULL,
  `last_seen_at` datetime(6) DEFAULT NULL,
  `metadata` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`metadata`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_device`
--

INSERT INTO `api_device` (`id`, `created_at`, `updated_at`, `name`, `code`, `device_type`, `status`, `is_enabled`, `firmware_version`, `api_token`, `last_seen_at`, `metadata`) VALUES
(1, '2026-05-09 10:13:24.715133', '2026-05-09 10:13:39.105308', 'Pump Main', 'pump-main', 'pump', 'online', 1, '', 'dev-placeholder-token-pump-main', '2026-05-09 10:13:39.105308', '{}'),
(2, '2026-05-09 10:13:39.095868', '2026-05-09 10:13:39.096841', 'ESP32 Main', 'esp32-main', 'controller', 'online', 1, '', 'dev-placeholder-token-esp32-main', '2026-05-09 10:13:39.096841', '{\"transport\": \"websocket\"}');

-- --------------------------------------------------------

--
-- Table structure for table `api_devicecommand`
--

CREATE TABLE `api_devicecommand` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `command` varchar(50) NOT NULL,
  `value` varchar(50) NOT NULL,
  `payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payload`)),
  `status` varchar(20) NOT NULL,
  `acked_at` datetime(6) DEFAULT NULL,
  `device_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `api_devicestate`
--

CREATE TABLE `api_devicestate` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `is_on` tinyint(1) NOT NULL,
  `desired_on` tinyint(1) NOT NULL,
  `last_command` varchar(50) NOT NULL,
  `last_value` varchar(50) NOT NULL,
  `extra` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`extra`)),
  `device_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_devicestate`
--

INSERT INTO `api_devicestate` (`id`, `created_at`, `updated_at`, `is_on`, `desired_on`, `last_command`, `last_value`, `extra`, `device_id`) VALUES
(1, '2026-05-09 10:13:39.107447', '2026-05-09 10:13:39.108962', 0, 0, 'telemetry_sync', 'off', '{}', 1);

-- --------------------------------------------------------

--
-- Table structure for table `api_estimationcycle`
--

CREATE TABLE `api_estimationcycle` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `sample_ts` datetime(6) NOT NULL,
  `cycle_index` int(10) UNSIGNED NOT NULL CHECK (`cycle_index` >= 0),
  `validation_status` varchar(32) NOT NULL,
  `validation_reason` longtext NOT NULL,
  `preprocess_status` varchar(20) NOT NULL,
  `cycle_status` varchar(40) NOT NULL,
  `adaptive_status` varchar(20) NOT NULL,
  `raw_soil_moisture` double DEFAULT NULL,
  `temperature` double DEFAULT NULL,
  `humidity` double DEFAULT NULL,
  `light` double DEFAULT NULL,
  `drip` double DEFAULT NULL,
  `mist` double DEFAULT NULL,
  `fan` double DEFAULT NULL,
  `arx_predicted` double DEFAULT NULL,
  `kf_x_prior` double DEFAULT NULL,
  `kf_P_prior` double DEFAULT NULL,
  `kf_innovation` double DEFAULT NULL,
  `kf_R` double DEFAULT NULL,
  `kf_K` double DEFAULT NULL,
  `kf_x_posterior` double DEFAULT NULL,
  `kf_P_posterior` double DEFAULT NULL,
  `latency_ms` double DEFAULT NULL,
  `error_message` longtext NOT NULL,
  `sensor_data_id` bigint(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_estimationcycle`
--

INSERT INTO `api_estimationcycle` (`id`, `created_at`, `updated_at`, `sample_ts`, `cycle_index`, `validation_status`, `validation_reason`, `preprocess_status`, `cycle_status`, `adaptive_status`, `raw_soil_moisture`, `temperature`, `humidity`, `light`, `drip`, `mist`, `fan`, `arx_predicted`, `kf_x_prior`, `kf_P_prior`, `kf_innovation`, `kf_R`, `kf_K`, `kf_x_posterior`, `kf_P_posterior`, `latency_ms`, `error_message`, `sensor_data_id`) VALUES
(1, '2026-05-09 10:13:39.116053', '2026-05-09 10:13:39.116053', '2026-05-09 10:13:39.088835', 0, 'valid', '', 'valid', 'ok', 'R_updated', 61.5, 28.5, 67.2, 5200, 0, 0, 0, NULL, 61.5, 1.05, 0, 0.95, 0.525, 61.5, 0.49874999999999997, 0.006499991286545992, '', 1);

-- --------------------------------------------------------

--
-- Table structure for table `api_sensordata`
--

CREATE TABLE `api_sensordata` (
  `id` bigint(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `temperature` decimal(5,2) DEFAULT NULL,
  `humidity` decimal(5,2) DEFAULT NULL,
  `light` decimal(10,2) DEFAULT NULL,
  `soil_moisture` decimal(5,2) DEFAULT NULL,
  `payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`payload`)),
  `recorded_at` datetime(6) NOT NULL,
  `received_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `api_sensordata`
--

INSERT INTO `api_sensordata` (`id`, `created_at`, `updated_at`, `temperature`, `humidity`, `light`, `soil_moisture`, `payload`, `recorded_at`, `received_at`) VALUES
(1, '2026-05-09 10:13:39.088835', '2026-05-09 10:13:39.088835', 28.50, 67.20, 5200.00, 61.50, '{}', '2026-05-09 10:13:39.088835', '2026-05-09 10:13:39.088835');

-- --------------------------------------------------------

--
-- Table structure for table `authtoken_token`
--

CREATE TABLE `authtoken_token` (
  `key` varchar(40) NOT NULL,
  `created` datetime(6) NOT NULL,
  `user_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_group`
--

CREATE TABLE `auth_group` (
  `id` int(11) NOT NULL,
  `name` varchar(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_group_permissions`
--

CREATE TABLE `auth_group_permissions` (
  `id` bigint(20) NOT NULL,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_permission`
--

CREATE TABLE `auth_permission` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `auth_permission`
--

INSERT INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
(1, 'Can add log entry', 1, 'add_logentry'),
(2, 'Can change log entry', 1, 'change_logentry'),
(3, 'Can delete log entry', 1, 'delete_logentry'),
(4, 'Can view log entry', 1, 'view_logentry'),
(5, 'Can add permission', 2, 'add_permission'),
(6, 'Can change permission', 2, 'change_permission'),
(7, 'Can delete permission', 2, 'delete_permission'),
(8, 'Can view permission', 2, 'view_permission'),
(9, 'Can add group', 3, 'add_group'),
(10, 'Can change group', 3, 'change_group'),
(11, 'Can delete group', 3, 'delete_group'),
(12, 'Can view group', 3, 'view_group'),
(13, 'Can add user', 4, 'add_user'),
(14, 'Can change user', 4, 'change_user'),
(15, 'Can delete user', 4, 'delete_user'),
(16, 'Can view user', 4, 'view_user'),
(17, 'Can add content type', 5, 'add_contenttype'),
(18, 'Can change content type', 5, 'change_contenttype'),
(19, 'Can delete content type', 5, 'delete_contenttype'),
(20, 'Can view content type', 5, 'view_contenttype'),
(21, 'Can add session', 6, 'add_session'),
(22, 'Can change session', 6, 'change_session'),
(23, 'Can delete session', 6, 'delete_session'),
(24, 'Can view session', 6, 'view_session'),
(25, 'Can add device', 7, 'add_device'),
(26, 'Can change device', 7, 'change_device'),
(27, 'Can delete device', 7, 'delete_device'),
(28, 'Can view device', 7, 'view_device'),
(29, 'Can add device state', 8, 'add_devicestate'),
(30, 'Can change device state', 8, 'change_devicestate'),
(31, 'Can delete device state', 8, 'delete_devicestate'),
(32, 'Can view device state', 8, 'view_devicestate'),
(33, 'Can add sensor data', 9, 'add_sensordata'),
(34, 'Can change sensor data', 9, 'change_sensordata'),
(35, 'Can delete sensor data', 9, 'delete_sensordata'),
(36, 'Can view sensor data', 9, 'view_sensordata'),
(37, 'Can add alert', 10, 'add_alert'),
(38, 'Can change alert', 10, 'change_alert'),
(39, 'Can delete alert', 10, 'delete_alert'),
(40, 'Can view alert', 10, 'view_alert'),
(41, 'Can add device command', 11, 'add_devicecommand'),
(42, 'Can change device command', 11, 'change_devicecommand'),
(43, 'Can delete device command', 11, 'delete_devicecommand'),
(44, 'Can view device command', 11, 'view_devicecommand'),
(45, 'Can add Control state', 12, 'add_controlstate'),
(46, 'Can change Control state', 12, 'change_controlstate'),
(47, 'Can delete Control state', 12, 'delete_controlstate'),
(48, 'Can view Control state', 12, 'view_controlstate'),
(49, 'Can add Control profile', 13, 'add_controlprofile'),
(50, 'Can change Control profile', 13, 'change_controlprofile'),
(51, 'Can delete Control profile', 13, 'delete_controlprofile'),
(52, 'Can view Control profile', 13, 'view_controlprofile'),
(53, 'Can add estimation cycle', 14, 'add_estimationcycle'),
(54, 'Can change estimation cycle', 14, 'change_estimationcycle'),
(55, 'Can delete estimation cycle', 14, 'delete_estimationcycle'),
(56, 'Can view estimation cycle', 14, 'view_estimationcycle'),
(57, 'Can add ampc recommendation', 15, 'add_ampcrecommendation'),
(58, 'Can change ampc recommendation', 15, 'change_ampcrecommendation'),
(59, 'Can delete ampc recommendation', 15, 'delete_ampcrecommendation'),
(60, 'Can view ampc recommendation', 15, 'view_ampcrecommendation');

-- --------------------------------------------------------

--
-- Table structure for table `auth_user`
--

CREATE TABLE `auth_user` (
  `id` int(11) NOT NULL,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `auth_user`
--

INSERT INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`) VALUES
(1, '!', NULL, 0, 'legacy_greenhouse_owner', '', '', '', 0, 0, '2026-05-09 05:50:42.363130'),
(2, '!', NULL, 1, 'local_admin', '', '', '', 1, 1, '2026-05-09 17:20:29.000000');

-- --------------------------------------------------------

--
-- Table structure for table `auth_user_groups`
--

CREATE TABLE `auth_user_groups` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `auth_user_user_permissions`
--

CREATE TABLE `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `django_admin_log`
--

CREATE TABLE `django_admin_log` (
  `id` int(11) NOT NULL,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) UNSIGNED NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `django_content_type`
--

CREATE TABLE `django_content_type` (
  `id` int(11) NOT NULL,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `django_content_type`
--

INSERT INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1, 'admin', 'logentry'),
(10, 'api', 'alert'),
(15, 'api', 'ampcrecommendation'),
(13, 'api', 'controlprofile'),
(12, 'api', 'controlstate'),
(7, 'api', 'device'),
(11, 'api', 'devicecommand'),
(8, 'api', 'devicestate'),
(14, 'api', 'estimationcycle'),
(9, 'api', 'sensordata'),
(3, 'auth', 'group'),
(2, 'auth', 'permission'),
(4, 'auth', 'user'),
(5, 'contenttypes', 'contenttype'),
(6, 'sessions', 'session');

-- --------------------------------------------------------

--
-- Table structure for table `django_migrations`
--

CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `django_migrations`
--

INSERT INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
(1, 'contenttypes', '0001_initial', '2026-05-09 10:13:02.020203'),
(2, 'auth', '0001_initial', '2026-05-09 10:13:02.181034'),
(3, 'admin', '0001_initial', '2026-05-09 10:13:02.218987'),
(4, 'admin', '0002_logentry_remove_auto_add', '2026-05-09 10:13:02.223398'),
(5, 'admin', '0003_logentry_add_action_flag_choices', '2026-05-09 10:13:02.228368'),
(6, 'api', '0001_initial', '2026-05-09 10:13:02.411389'),
(7, 'api', '0002_sensorcurrent', '2026-05-09 10:13:02.439176'),
(8, 'api', '0003_controlstate', '2026-05-09 10:13:02.446068'),
(9, 'api', '0004_delete_controlstate_and_more', '2026-05-09 10:13:02.557140'),
(10, 'api', '0005_controlstate', '2026-05-09 10:13:02.563215'),
(11, 'api', '0006_controlprofile_alter_device_device_type_and_more', '2026-05-09 10:13:02.684181'),
(12, 'contenttypes', '0002_remove_content_type_name', '2026-05-09 10:13:02.711787'),
(13, 'auth', '0002_alter_permission_name_max_length', '2026-05-09 10:13:02.731222'),
(14, 'auth', '0003_alter_user_email_max_length', '2026-05-09 10:13:02.739108'),
(15, 'auth', '0004_alter_user_username_opts', '2026-05-09 10:13:02.744472'),
(16, 'auth', '0005_alter_user_last_login_null', '2026-05-09 10:13:02.764352'),
(17, 'auth', '0006_require_contenttypes_0002', '2026-05-09 10:13:02.766340'),
(18, 'auth', '0007_alter_validators_add_error_messages', '2026-05-09 10:13:02.774468'),
(19, 'auth', '0008_alter_user_username_max_length', '2026-05-09 10:13:02.784956'),
(20, 'auth', '0009_alter_user_last_name_max_length', '2026-05-09 10:13:02.793712'),
(21, 'auth', '0010_alter_group_name_max_length', '2026-05-09 10:13:02.805181'),
(22, 'auth', '0011_update_proxy_permissions', '2026-05-09 10:13:02.818260'),
(23, 'auth', '0012_alter_user_first_name_max_length', '2026-05-09 10:13:02.826208'),
(24, 'sessions', '0001_initial', '2026-05-09 10:13:02.841009');

-- --------------------------------------------------------

--
-- Table structure for table `django_session`
--

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `evaluation_summaries`
--

CREATE TABLE `evaluation_summaries` (
  `id` int(11) NOT NULL,
  `run_id` int(11) NOT NULL,
  `slice_type` varchar(15) NOT NULL,
  `n_samples` int(11) NOT NULL,
  `n_valid` int(11) NOT NULL,
  `n_skipped` int(11) NOT NULL,
  `n_error` int(11) NOT NULL,
  `rmse_arx` double DEFAULT NULL,
  `mae_arx` double DEFAULT NULL,
  `rmse_filtered` double DEFAULT NULL,
  `mae_filtered` double DEFAULT NULL,
  `var_diff_raw` double DEFAULT NULL,
  `var_diff_filtered` double DEFAULT NULL,
  `variance_reduction` double DEFAULT NULL,
  `rmse_ratio` double DEFAULT NULL,
  `mae_ratio` double DEFAULT NULL,
  `innovation_mean` double DEFAULT NULL,
  `innovation_std` double DEFAULT NULL,
  `innovation_max_abs` double DEFAULT NULL,
  `R_mean` double DEFAULT NULL,
  `R_min_observed` double DEFAULT NULL,
  `R_max_observed` double DEFAULT NULL,
  `P_mean` double DEFAULT NULL,
  `P_max` double DEFAULT NULL,
  `pass_variance_reduction` tinyint(1) DEFAULT NULL,
  `pass_rmse_guardrail` tinyint(1) DEFAULT NULL,
  `pass_mae_guardrail` tinyint(1) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `n_r_updated` int(11) NOT NULL,
  `n_r_skipped` int(11) NOT NULL,
  `n_adaptive_skipped` int(11) NOT NULL,
  `latency_mean_ms` double DEFAULT NULL,
  `latency_p95_ms` double DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `experiment_configs`
--

CREATE TABLE `experiment_configs` (
  `id` int(11) NOT NULL,
  `run_id` int(11) NOT NULL,
  `x0` double NOT NULL,
  `P0` double NOT NULL,
  `Q` double NOT NULL,
  `R0` double NOT NULL,
  `R_min` double NOT NULL,
  `R_max` double NOT NULL,
  `alpha` double NOT NULL,
  `raw_config_json` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `experiment_configs`
--

INSERT INTO `experiment_configs` (`id`, `run_id`, `x0`, `P0`, `Q`, `R0`, `R_min`, `R_max`, `alpha`, `raw_config_json`, `created_at`) VALUES
(1, 1, 58, 1, 0.05, 1, 0.05, 25, 0.95, '{\"name\": \"greenhouse_data.csv offline replay\", \"dataset_source\": \"D:\\\\HK6\\\\PBL\\\\Demo_kalman\\\\ARX\\\\greenhouse_data.csv\", \"x0\": 58.0, \"P0\": 1.0, \"Q\": 0.05, \"R0\": 1.0, \"R_min\": 0.05, \"R_max\": 25.0, \"alpha\": 0.95, \"train_ratio\": 0.6, \"val_ratio\": 0.2, \"test_ratio\": 0.2, \"arx_na\": 2, \"arx_nb\": 2, \"arx_nk\": 1, \"arx_input_cols\": [\"Temperature\", \"Humidity\", \"Light\", \"Drip\", \"Mist\", \"Fan\"], \"preprocessing_policy\": \"keep_last\"}', '2026-04-17 13:06:33.005611');

-- --------------------------------------------------------

--
-- Table structure for table `experiment_runs`
--

CREATE TABLE `experiment_runs` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `run_type` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL,
  `dataset_source` varchar(512) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `notes` longtext DEFAULT NULL,
  `greenhouse_id` int(11) NOT NULL
) ;

--
-- Dumping data for table `experiment_runs`
--

INSERT INTO `experiment_runs` (`id`, `name`, `run_type`, `status`, `dataset_source`, `created_at`, `started_at`, `completed_at`, `notes`, `greenhouse_id`) VALUES
(1, 'demo kalman', 'live', 'completed', 'D:\\HK6\\PBL\\Demo_kalman\\ARX\\greenhouse_data.csv', '2026-04-17 13:06:32.985390', '2026-04-17 13:06:33.018970', '2026-04-17 13:06:56.427087', 'Imported full ARX/greenhouse_data.csv for dashboard demo', 1);

-- --------------------------------------------------------

--
-- Table structure for table `greenhouses`
--

CREATE TABLE `greenhouses` (
  `id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `location` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `notes` longtext DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `owner_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `greenhouses`
--

INSERT INTO `greenhouses` (`id`, `name`, `location`, `is_active`, `notes`, `created_at`, `updated_at`, `owner_id`) VALUES
(1, 'Default Greenhouse', NULL, 1, NULL, '2026-05-09 05:50:42.366528', '2026-05-09 05:50:42.366528', 1);

-- --------------------------------------------------------

--
-- Table structure for table `greenhouse_control_profiles`
--

CREATE TABLE `greenhouse_control_profiles` (
  `id` int(11) NOT NULL,
  `crop_name` varchar(100) NOT NULL,
  `crop_kc` double NOT NULL,
  `target_low` double NOT NULL,
  `target_high` double NOT NULL,
  `pump_max_seconds` double NOT NULL,
  `soft_daily_pump_cap_seconds` double NOT NULL,
  `actuator_enabled` tinyint(1) NOT NULL,
  `step_seconds` int(11) NOT NULL,
  `horizon_steps` int(11) NOT NULL,
  `pump_min_seconds` double NOT NULL,
  `pump_grid_seconds` double NOT NULL,
  `cost_band_violation` double NOT NULL,
  `cost_water_use` double NOT NULL,
  `cost_switching` double NOT NULL,
  `cost_daily_cap_excess` double NOT NULL,
  `cost_terminal_band_violation` double NOT NULL,
  `adaptive_enabled` tinyint(1) NOT NULL,
  `adaptive_bias_window` int(11) NOT NULL,
  `adaptive_max_abs_bias` double NOT NULL,
  `safety_stale_after_seconds` int(11) NOT NULL,
  `actuator_url` varchar(2048) DEFAULT NULL,
  `actuator_bearer_token_env` varchar(128) DEFAULT NULL,
  `actuator_timeout_seconds` double NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `greenhouse_id` int(11) NOT NULL
) ;

-- --------------------------------------------------------

--
-- Indexes for table `api_alert`
--
ALTER TABLE `api_alert`
  ADD PRIMARY KEY (`id`),
  ADD KEY `api_alert_device_id_04f4dd80_fk_api_device_id` (`device_id`),
  ADD KEY `api_alert_sensor_data_id_f7cf8ccd_fk_api_sensordata_id` (`sensor_data_id`),
  ADD KEY `api_alert_happened_at_528cba8b` (`happened_at`);

--
-- Indexes for table `api_ampcrecommendation`
--
ALTER TABLE `api_ampcrecommendation`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ampc_created_safety_idx` (`created_at`,`safety_status`),
  ADD KEY `api_ampcrecommendati_device_command_id_82023858_fk_api_devic` (`device_command_id`),
  ADD KEY `api_ampcrecommendati_estimation_id_a64d4d8a_fk_api_estim` (`estimation_id`),
  ADD KEY `api_ampcrecommendati_sensor_data_id_35076718_fk_api_senso` (`sensor_data_id`);

--
-- Indexes for table `api_controlprofile`
--
ALTER TABLE `api_controlprofile`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `singleton_key` (`singleton_key`);

--
-- Indexes for table `api_controlstate`
--
ALTER TABLE `api_controlstate`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `singleton_key` (`singleton_key`);

--
-- Indexes for table `api_device`
--
ALTER TABLE `api_device`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `code` (`code`),
  ADD UNIQUE KEY `api_token` (`api_token`);

--
-- Indexes for table `api_devicecommand`
--
ALTER TABLE `api_devicecommand`
  ADD PRIMARY KEY (`id`),
  ADD KEY `api_devicecommand_device_id_0747feb3_fk_api_device_id` (`device_id`),
  ADD KEY `cmd_status_created_idx` (`status`,`created_at`);

--
-- Indexes for table `api_devicestate`
--
ALTER TABLE `api_devicestate`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `device_id` (`device_id`);

--
-- Indexes for table `api_estimationcycle`
--
ALTER TABLE `api_estimationcycle`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `sensor_data_id` (`sensor_data_id`),
  ADD KEY `est_sample_id_idx` (`sample_ts`,`id`),
  ADD KEY `est_status_ts_idx` (`cycle_status`,`sample_ts`),
  ADD KEY `api_estimationcycle_sample_ts_0ac1c1ec` (`sample_ts`),
  ADD KEY `api_estimationcycle_cycle_index_5a22920c` (`cycle_index`);

--
-- Indexes for table `api_sensordata`
--
ALTER TABLE `api_sensordata`
  ADD PRIMARY KEY (`id`),
  ADD KEY `api_sensordata_recorded_at_eb0c283a` (`recorded_at`),
  ADD KEY `api_sensordata_received_at_79476c95` (`received_at`),
  ADD KEY `sensor_recorded_idx` (`recorded_at`);

--
-- Indexes for table `authtoken_token`
--
ALTER TABLE `authtoken_token`
  ADD PRIMARY KEY (`key`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- Indexes for table `auth_group`
--
ALTER TABLE `auth_group`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`);

--
-- Indexes for table `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  ADD KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`);

--
-- Indexes for table `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`);

--
-- Indexes for table `auth_user`
--
ALTER TABLE `auth_user`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  ADD KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`);

--
-- Indexes for table `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  ADD KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`);

--
-- Indexes for table `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  ADD KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`);

--
-- Indexes for table `django_content_type`
--
ALTER TABLE `django_content_type`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`);

--
-- Indexes for table `django_migrations`
--
ALTER TABLE `django_migrations`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `django_session`
--
ALTER TABLE `django_session`
  ADD PRIMARY KEY (`session_key`),
  ADD KEY `django_session_expire_date_a5c62663` (`expire_date`);

--
-- Indexes for table `evaluation_summaries`
--
ALTER TABLE `evaluation_summaries`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `evaluation_summaries_run_id_slice_type_ed0610e0_uniq` (`run_id`,`slice_type`);

--
-- Indexes for table `experiment_configs`
--
ALTER TABLE `experiment_configs`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `run_id` (`run_id`);

--
-- Indexes for table `experiment_runs`
--
ALTER TABLE `experiment_runs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_runs_status` (`status`),
  ADD KEY `idx_runs_created` (`created_at`),
  ADD KEY `idx_runs_greenhouse_created` (`greenhouse_id`,`created_at`),
  ADD KEY `idx_runs_greenhouse_status` (`greenhouse_id`,`status`);

--
-- Indexes for table `greenhouses`
--
ALTER TABLE `greenhouses`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_greenhouses_owner_name` (`owner_id`,`name`),
  ADD KEY `idx_greenhouses_owner_active` (`owner_id`,`is_active`),
  ADD KEY `idx_greenhouses_created` (`created_at`);

--
-- Indexes for table `greenhouse_control_profiles`
--
ALTER TABLE `greenhouse_control_profiles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `greenhouse_id` (`greenhouse_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `api_alert`
--
ALTER TABLE `api_alert`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `api_ampcrecommendation`
--
ALTER TABLE `api_ampcrecommendation`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `api_controlprofile`
--
ALTER TABLE `api_controlprofile`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `api_controlstate`
--
ALTER TABLE `api_controlstate`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `api_device`
--
ALTER TABLE `api_device`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `api_devicecommand`
--
ALTER TABLE `api_devicecommand`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `api_devicestate`
--
ALTER TABLE `api_devicestate`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `api_estimationcycle`
--
ALTER TABLE `api_estimationcycle`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `api_sensordata`
--
ALTER TABLE `api_sensordata`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `auth_group`
--
ALTER TABLE `auth_group`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `auth_permission`
--
ALTER TABLE `auth_permission`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=61;

--
-- AUTO_INCREMENT for table `auth_user`
--
ALTER TABLE `auth_user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `django_admin_log`
--
ALTER TABLE `django_admin_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `django_content_type`
--
ALTER TABLE `django_content_type`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT for table `django_migrations`
--
ALTER TABLE `django_migrations`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT for table `evaluation_summaries`
--
ALTER TABLE `evaluation_summaries`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `experiment_configs`
--
ALTER TABLE `experiment_configs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `experiment_runs`
--
ALTER TABLE `experiment_runs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `greenhouses`
--
ALTER TABLE `greenhouses`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `greenhouse_control_profiles`
--
ALTER TABLE `greenhouse_control_profiles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `api_alert`
--
ALTER TABLE `api_alert`
  ADD CONSTRAINT `api_alert_device_id_04f4dd80_fk_api_device_id` FOREIGN KEY (`device_id`) REFERENCES `api_device` (`id`),
  ADD CONSTRAINT `api_alert_sensor_data_id_f7cf8ccd_fk_api_sensordata_id` FOREIGN KEY (`sensor_data_id`) REFERENCES `api_sensordata` (`id`);

--
-- Constraints for table `api_ampcrecommendation`
--
ALTER TABLE `api_ampcrecommendation`
  ADD CONSTRAINT `api_ampcrecommendati_device_command_id_82023858_fk_api_devic` FOREIGN KEY (`device_command_id`) REFERENCES `api_devicecommand` (`id`),
  ADD CONSTRAINT `api_ampcrecommendati_estimation_id_a64d4d8a_fk_api_estim` FOREIGN KEY (`estimation_id`) REFERENCES `api_estimationcycle` (`id`),
  ADD CONSTRAINT `api_ampcrecommendati_sensor_data_id_35076718_fk_api_senso` FOREIGN KEY (`sensor_data_id`) REFERENCES `api_sensordata` (`id`);

--
-- Constraints for table `api_devicecommand`
--
ALTER TABLE `api_devicecommand`
  ADD CONSTRAINT `api_devicecommand_device_id_0747feb3_fk_api_device_id` FOREIGN KEY (`device_id`) REFERENCES `api_device` (`id`);

--
-- Constraints for table `api_devicestate`
--
ALTER TABLE `api_devicestate`
  ADD CONSTRAINT `api_devicestate_device_id_94e73169_fk_api_device_id` FOREIGN KEY (`device_id`) REFERENCES `api_device` (`id`);

--
-- Constraints for table `api_estimationcycle`
--
ALTER TABLE `api_estimationcycle`
  ADD CONSTRAINT `api_estimationcycle_sensor_data_id_fd2b853d_fk_api_sensordata_id` FOREIGN KEY (`sensor_data_id`) REFERENCES `api_sensordata` (`id`);

--
-- Constraints for table `auth_group_permissions`
--
ALTER TABLE `auth_group_permissions`
  ADD CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`);

--
-- Constraints for table `auth_permission`
--
ALTER TABLE `auth_permission`
  ADD CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`);

--
-- Constraints for table `auth_user_groups`
--
ALTER TABLE `auth_user_groups`
  ADD CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  ADD CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `auth_user_user_permissions`
--
ALTER TABLE `auth_user_user_permissions`
  ADD CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  ADD CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `django_admin_log`
--
ALTER TABLE `django_admin_log`
  ADD CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  ADD CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `evaluation_summaries`
--
ALTER TABLE `evaluation_summaries`
  ADD CONSTRAINT `evaluation_summaries_run_id_b31a0c9c_fk_experiment_runs_id` FOREIGN KEY (`run_id`) REFERENCES `experiment_runs` (`id`);

--
-- Constraints for table `experiment_configs`
--
ALTER TABLE `experiment_configs`
  ADD CONSTRAINT `experiment_configs_run_id_c741522d_fk_experiment_runs_id` FOREIGN KEY (`run_id`) REFERENCES `experiment_runs` (`id`);

--
-- Constraints for table `experiment_runs`
--
ALTER TABLE `experiment_runs`
  ADD CONSTRAINT `experiment_runs_greenhouse_id_15ae0066_fk_greenhouses_id` FOREIGN KEY (`greenhouse_id`) REFERENCES `greenhouses` (`id`);

--
-- Constraints for table `greenhouses`
--
ALTER TABLE `greenhouses`
  ADD CONSTRAINT `greenhouses_owner_id_32544aaf_fk_auth_user_id` FOREIGN KEY (`owner_id`) REFERENCES `auth_user` (`id`);

--
-- Constraints for table `greenhouse_control_profiles`
--
ALTER TABLE `greenhouse_control_profiles`
  ADD CONSTRAINT `greenhouse_control_p_greenhouse_id_e01130e3_fk_greenhous` FOREIGN KEY (`greenhouse_id`) REFERENCES `greenhouses` (`id`);

--
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
