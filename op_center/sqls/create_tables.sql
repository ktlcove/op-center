DROP DATABASE IF EXISTS `op-center`;

CREATE DATABASE IF NOT EXISTS `op-center`
  DEFAULT CHARSET utf8;

USE `op-center`;


CREATE TABLE `group` (
  `id`          INT         NOT NULL        AUTO_INCREMENT PRIMARY KEY,
  `name`        VARCHAR(50) NOT NULL UNIQUE,
  `description` TEXT        NULL,
  `c_time`      DATETIME    NOT NULL        DEFAULT CURRENT_TIMESTAMP,
  `m_time`      DATETIME    NOT NULL        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX (`id`, `name`, `c_time`, `m_time`)
);

CREATE TABLE `user` (
  `id`             INT          NOT NULL        AUTO_INCREMENT PRIMARY KEY,
  `name`           VARCHAR(50)  NOT NULL UNIQUE,
  `alias`          VARCHAR(50)  NOT NULL,
  `mail`           VARCHAR(150) NOT NULL,
  `type`           VARCHAR(20)  NOT NULL        DEFAULT 'ldap',
  `password`       VARCHAR(120) NULL,
  `token`          VARCHAR(120) NOT NULL UNIQUE,
  `basic_group_id` INT          NOT NULL,
  `c_time`         DATETIME     NOT NULL        DEFAULT CURRENT_TIMESTAMP,
  `m_time`         DATETIME     NOT NULL        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (basic_group_id) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  INDEX (`id`, `name`, `alias`, `mail`, `type`, `token`,
         `basic_group_id`, `c_time`, `m_time`)
);

CREATE TABLE `user_group_relation` (
  `user_id`   INT NOT NULL,
  `group_id`  INT NOT NULL,
  `character` INT NOT NULL,

  PRIMARY KEY (`user_id`, `group_id`),

  FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  FOREIGN KEY (`group_id`) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  INDEX (`character`)
);

CREATE TABLE `group_permission` (
  `group_id`   INT          NOT NULL,
  `type`       VARCHAR(20)  NOT NULL,
  `permission` VARCHAR(100) NOT NULL,
  `character`  INT          NOT NULL,

  FOREIGN KEY (`group_id`) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  PRIMARY KEY (`group_id`, `type`, `permission`),

  INDEX (`character`)
);

CREATE TABLE `host` (
  `ip`     VARCHAR(20) NOT NULL PRIMARY KEY,
  `basic`  JSON        NOT NULL,
  `issystem` JSON        NOT NULL,
  `envs`   JSON        NOT NULL,
  `ok`     BOOL        NOT NULL             DEFAULT FALSE,
  `c_time` DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP,
  `m_time` DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX (`ok`, `c_time`, `m_time`)

);

CREATE TABLE `workflow` (
  `id`          INT         NOT NULL             AUTO_INCREMENT PRIMARY KEY,
  `name`        VARCHAR(50) NOT NULL,
  `description` TEXT        NULL,
  `group_id`    INT         NULL,
  `type`        VARCHAR(20) NOT NULL,
  `steps`       JSON        NOT NULL,
  `basic`       JSON        NOT NULL,
  `envs`        JSON        NOT NULL,
  `args`        JSON        NOT NULL,
  `c_time`      DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP,
  `m_time`      DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (`group_id`) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `_uc_name_group_id` UNIQUE (`name`, `group_id`),

  INDEX (`id`, `name`, `group_id`, `type`, `c_time`, `m_time`)
);

CREATE TABLE `host_filter` (
  `id`          INT         NOT NULL             AUTO_INCREMENT PRIMARY KEY,
  `name`        VARCHAR(50) NOT NULL,
  `description` TEXT        NULL,
  `group_id`    INT         NULL,
  `filters`     JSON        NOT NULL,
  `c_time`      DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP,
  `m_time`      DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (`group_id`) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `_uc_name_group_id` UNIQUE (`name`, `group_id`),

  INDEX (`id`, `name`, `group_id`, `c_time`, `m_time`)
);

CREATE TABLE `operator` (
  `id`          INT         NOT NULL             AUTO_INCREMENT PRIMARY KEY,
  `name`        VARCHAR(50) NOT NULL UNIQUE,
  `group_id`    INT         NULL,
  `description` TEXT        NULL,
  `type`        VARCHAR(20) NOT NULL,
  `mq_link`     JSON        NOT NULL,
  `c_time`      DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP,
  `m_time`      DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX (`id`, `name`, `group_id`, `type`, `c_time`, `m_time`)
);

CREATE TABLE `operation` (
  `id`             INT         NOT NULL             AUTO_INCREMENT PRIMARY KEY,
  `name`           VARCHAR(50) NOT NULL,
  `description`    TEXT        NULL,
  `group_id`       INT         NULL,
  `workflow_id`    INT         NOT NULL,
  `host_filter_id` INT         NOT NULL,
  `operator_id`    INT         NULL,
  `cache`          JSON        NOT NULL,
  `c_time`         DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP,
  `m_time`         DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (`group_id`) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  FOREIGN KEY (`workflow_id`) REFERENCES `workflow` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  FOREIGN KEY (`host_filter_id`) REFERENCES `host_filter` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  FOREIGN KEY (`operator_id`) REFERENCES `operator` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  CONSTRAINT `_uc_name_group_id` UNIQUE (`name`, `group_id`),
  INDEX (`id`, `name`, `group_id`, `c_time`, `m_time`)
);

CREATE TABLE `task` (
  `id`             VARCHAR(50) NOT NULL   PRIMARY KEY,
  `group_id`       INT         NULL,
  `operation_id`   INT         NOT NULL,
  `workflow`       JSON        NOT NULL,
  `hosts`          JSON        NOT NULL,
  `operator_id`    INT         NOT NULL,
  `running_kwargs` JSON        NOT NULL,
  `runner`         VARCHAR(50) NOT NULL,
  `status`         JSON        NOT NULL,
  `result`         JSON        NOT NULL,
  `c_time`         DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP,
  `m_time`         DATETIME    NOT NULL             DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `f_time`         DATETIME    NULL,

  FOREIGN KEY (`group_id`) REFERENCES `group` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  FOREIGN KEY (`operation_id`) REFERENCES `operation` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  FOREIGN KEY (`operator_id`) REFERENCES `operator` (`id`)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,

  INDEX (`id`, `group_id`, `c_time`, `m_time`, `f_time`, `runner`)

);