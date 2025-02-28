SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

CREATE SCHEMA IF NOT EXISTS `Libreria` DEFAULT CHARACTER SET utf8 ;
CREATE DATABASE Libreria;
USE Libreria;

-- Tabla de Libros
CREATE TABLE Libro (
  idLibro INT NOT NULL AUTO_INCREMENT,
  Nombre VARCHAR(45) NOT NULL,
  Editorial VARCHAR(45) NOT NULL,
  Edicion VARCHAR(45) NULL,
  Estado VARCHAR(45) NOT NULL,
  Cantidad INT NOT NULL,
  PRIMARY KEY (idLibro),
  UNIQUE INDEX idLibro_UNIQUE (idLibro ASC)
) ENGINE = InnoDB;

-- Tabla de Personal_Manage
CREATE TABLE Personal_Manage (
  IDpersonal INT NOT NULL AUTO_INCREMENT,
  Usuario VARCHAR(45) NOT NULL,
  Contrasena VARCHAR(45) NOT NULL,
  Nombre VARCHAR(45) NOT NULL,
  Apellido VARCHAR(45) NOT NULL,
  Rol VARCHAR(45) NOT NULL,
  IDLibro INT NULL,
  PRIMARY KEY (IDpersonal),
  UNIQUE INDEX IDpersonal_UNIQUE (IDpersonal ASC),
  INDEX IDLibro_idx (IDLibro ASC),
  CONSTRAINT FK_Personal_Libro
    FOREIGN KEY (IDLibro)
    REFERENCES Libro (idLibro)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Tabla de Administradores
CREATE TABLE Administradores (
  IDpersonal INT NOT NULL AUTO_INCREMENT,
  Usuario VARCHAR(45) NOT NULL,
  Contrasena VARCHAR(45) NOT NULL,
  Nombre VARCHAR(45) NOT NULL,
  Apellido VARCHAR(45) NOT NULL,
  PRIMARY KEY (IDpersonal)
) ENGINE = InnoDB;

-- Tabla de Direcciones
CREATE TABLE Direcciones (
  idDirecciones INT NOT NULL AUTO_INCREMENT,
  Calle VARCHAR(45) NOT NULL,
  Colonia VARCHAR(45) NOT NULL,
  CP VARCHAR(50) NOT NULL,
  NumExterior INT NULL,
  NumInterior INT NOT NULL,
  NumContacto VARCHAR(15) NOT NULL,
  PRIMARY KEY (idDirecciones)
) ENGINE = InnoDB;

-- Tabla de Clientes
CREATE TABLE Clientes (
  idClientes INT NOT NULL AUTO_INCREMENT,
  Nombre VARCHAR(45) NOT NULL,
  Apellidos VARCHAR(45) NOT NULL,
  Email VARCHAR(45) NOT NULL,
  Usuario VARCHAR(45) NOT NULL,
  Contrasena VARCHAR(45) NOT NULL,
  IDireccion INT NOT NULL,
  PRIMARY KEY (idClientes),
  INDEX IDDireccion_idx (IDireccion ASC),
  CONSTRAINT FK_Clientes_Direcciones
    FOREIGN KEY (IDireccion)
    REFERENCES Direcciones (idDirecciones)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE = InnoDB;

-- Tabla de Ventas
CREATE TABLE Ventas (
  IDVentas INT NOT NULL AUTO_INCREMENT,
  Fecha DATE NULL,
  Monto FLOAT NULL,
  TipoPago VARCHAR(45) NOT NULL,
  ID_libro INT NOT NULL,
  IDClientes INT NULL,
  PRIMARY KEY (IDVentas),
  UNIQUE INDEX IDVentas_UNIQUE (IDVentas ASC),
  INDEX ID_Libro_idx (ID_Libro ASC),
  INDEX IDCliente_idx (IDClientes ASC),
  CONSTRAINT FK_Ventas_Libro
    FOREIGN KEY (ID_libro)
    REFERENCES Libro (idLibro)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT FK_Ventas_Clientes
    FOREIGN KEY (IDClientes)
    REFERENCES Clientes (idClientes)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE = InnoDB;
INSERT INTO `Libro` (idLibro,Nombre,Editorial,Edicion,Estado,Cantidad) VALUES (10,'Harry Potter','ING','1','NoStock',0);
INSERT INTO `Libro` (idLibro,Nombre,Editorial,Edicion,Estado,Cantidad) VALUES (11,'El Quijote','Porrua','5','Stock',200);
INSERT INTO `Libro` (idLibro,Nombre,Editorial,Edicion,Estado,Cantidad) VALUES (12,'11 Minutos','Paulo Cohelo','11','Stock',50);
INSERT INTO `Administradores` (Usuario,Contrasena,Nombre,Apellido) VALUES ("btoadmin","cisco123", "Alberto", "Aguirre");
SELECT * FROM Administradores;
SELECT * FROM Libro
SELECT * FROM Clientes
drop database Libreria

DELIMITER $$

CREATE PROCEDURE AgregarLibro(
    IN p_nombre VARCHAR(45),
    IN p_editorial VARCHAR(45),
    IN p_edicion VARCHAR(45),
    IN p_estado VARCHAR(45),
    IN p_cantidad INT
)
BEGIN
    INSERT INTO Libro (Nombre, Editorial, Edicion, Estado, Cantidad)
    VALUES (p_nombre, p_editorial, p_edicion, p_estado, p_cantidad);
END$$

DELIMITER ;
select * from Libro;
DELIMITER $$

CREATE PROCEDURE ObtenerLibros()
BEGIN
    SELECT * FROM Libro;
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE EditarLibro(
    IN p_id INT,
    IN p_nombre VARCHAR(45),
    IN p_editorial VARCHAR(45),
    IN p_edicion VARCHAR(45),
    IN p_estado VARCHAR(45),
    IN p_cantidad INT
)
BEGIN
    UPDATE Libro
    SET Nombre = p_nombre, Editorial = p_editorial, Edicion = p_edicion, Estado = p_estado, Cantidad = p_cantidad
    WHERE idLibro = p_id;
END$$

DELIMITER ;
DELIMITER $$

CREATE PROCEDURE EliminarLibro(IN p_id INT)
BEGIN
    DELETE FROM Libro WHERE idLibro = p_id;
END$$

DELIMITER ;
select * from Libro;

ALTER TABLE Administradores MODIFY COLUMN Contrasena VARCHAR(60);
ALTER TABLE Clientes MODIFY COLUMN Contrasena VARCHAR(60);

