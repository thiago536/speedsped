cd C:\Program Files\PostgreSQL\15\bin
@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\2irmaossolanea.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% 2irmaossolanea
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% 2irmaossolanea

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\3F.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% 3F
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% 3F

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\3RB.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% 3RB
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% 3RB

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Ademir.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Ademir
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Ademir

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Aguadoce.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aguadoce
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aguadoce

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Algodao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Algodao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Algodao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Alianca.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Alianca
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Alianca

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Aliancaconv.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aliancaconv
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aliancaconv

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Aliancaconv1.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aliancaconv1
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aliancaconv1

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\All.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% All
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% All

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Alle.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Alle
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Alle

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Amigao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Amigao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Amigao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Andrade.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Andrade
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Andrade

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Anelbrejo.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Anelbrejo
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Anelbrejo

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Angicos.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Angicos
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Angicos

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\angicosacs.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% angicosacs
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% angicosacs

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Angicosteste.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Angicosteste
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Angicosteste

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Aparecida.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aparecida
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Aparecida

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Atualize.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Atualize
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Atualize

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\B2.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% B2
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% B2

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Bandeirantescg.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bandeirantescg
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bandeirantescg

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Barauna.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Barauna
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Barauna

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Belavista.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Belavista
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Belavista

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Bell.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bell
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bell

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Bilosao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bilosao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bilosao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\BM.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% BM
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% BM

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Boavista.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Boavista
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Boavista

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Bomjesus.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bomjesus
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Bomjesus

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Borborema.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Borborema
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Borborema

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Brasil.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Brasil
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Brasil

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Buzinao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Buzinao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Buzinao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Cajazeiras.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cajazeiras
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cajazeiras

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Caju.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Caju
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Caju

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Canaa.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Canaa
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Canaa

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Canarinho.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Canarinho
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Canarinho

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Candelaria.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Candelaria
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Candelaria

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Casanova.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Casanova
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Casanova

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Catingueira.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Catingueira
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Catingueira

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Conceicaomarcacao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Conceicaomarcacao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Conceicaomarcacao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Cordeiro.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cordeiro
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cordeiro

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Correia.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Correia
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Correia

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Creddeda.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Creddeda
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Creddeda

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Cross.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cross
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cross

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Cubati.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cubati
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cubati

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Cubati2.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cubati2
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Cubati2

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Daserra.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Daserra
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Daserra

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Dedejaime.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Dedejaime
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Dedejaime

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Demonstracao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Demonstracao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Demonstracao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\DLM.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% DLM
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% DLM

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\DV.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% DV
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% DV

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Estacada.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Estacada
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Estacada

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Estrada.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Estrada
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Estrada

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Expresso.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Expresso
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Expresso

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Extremo.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Extremo
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Extremo

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Fagundes.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Fagundes
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Fagundes

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\FDS.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% FDS
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% FDS

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Feitosa.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Feitosa
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Feitosa

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Feitosaconv.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Feitosaconv
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Feitosaconv

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\FerreiraeTavares.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% FerreiraeTavares
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% FerreiraeTavares

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Flores.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Flores
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Flores

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Gravata.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Gravata
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Gravata

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Guerra.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Guerra
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Guerra

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Gurinhem.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Gurinhem
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Gurinhem

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\H7conv.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% H7conv
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% H7conv

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Inovacao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Inovacao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Inovacao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Itamatay.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Itamatay
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Itamatay

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\JE.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JE
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JE

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\JM.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JM
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JM

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Joaopedro.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Joaopedro
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Joaopedro

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\JR.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JR
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JR

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\JV.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JV
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% JV

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Laisxii.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Laisxii
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Laisxii

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Lico.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Lico
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Lico

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Lucena.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Lucena
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Lucena

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Lucenao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Lucenao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Lucenao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\M2.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% M2
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% M2

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Maerainha.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Maerainha
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Maerainha

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Maranhao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Maranhao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Maranhao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Marinhos.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Marinhos
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Marinhos

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Marka.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Marka
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Marka

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Mastodonte.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Mastodonte
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Mastodonte

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Milagres.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Milagres
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Milagres

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Montesinai.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Montesinai
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Montesinai

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Novaitatuba.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Novaitatuba
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Novaitatuba

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Nsc.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Nsc
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Nsc

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Nsfatima.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Nsfatima
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Nsfatima

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Nslourdesaguabranca.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Nslourdesaguabranca
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Nslourdesaguabranca

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Padrecicero.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Padrecicero
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Padrecicero

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Padreciceronovacruz.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Padreciceronovacruz
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Padreciceronovacruz

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Padreciceropassaefica.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Padreciceropassaefica
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Padreciceropassaefica

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Paulino.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Paulino
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Paulino

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Pedroramos.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Pedroramos
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Pedroramos

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Petrobravo.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Petrobravo
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Petrobravo

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Pinheirao.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Pinheirao
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Pinheirao

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Plasvam.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Plasvam
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Plasvam

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Postodosol.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Postodosol
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Postodosol

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Postoesperanca.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Postoesperanca
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Postoesperanca

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\RDL.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% RDL
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% RDL

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Realizza.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Realizza
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Realizza

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Redepazlucas.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Redepazlucas
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Redepazlucas

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Redeserrabranca.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Redeserrabranca
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Redeserrabranca

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Remigio.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Remigio
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Remigio

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\RM.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% RM
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% RM

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\RRauto.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% RRauto
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% RRauto

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sabugi.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sabugi
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sabugi

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santacruz.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santacruz
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santacruz

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santafe.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santafe
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santafe

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santaluziadocariri.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santaluziadocariri
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santaluziadocariri

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santarosa.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santarosa
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santarosa

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santavitoria.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=010248056
   echo on
   bin\pg_dump -h 187.45.181.113 -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santavitoria
pg_dump -h 187.45.181.113 -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santavitoria

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santiago.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santiago
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santiago

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santoantoniogba.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santoantoniogba
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santoantoniogba

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Santosiv.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santosiv
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Santosiv

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saobenedito.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saobenedito
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saobenedito

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saodomingos.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saodomingos
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saodomingos

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saofranciscoararuna.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saofranciscoararuna
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saofranciscoararuna

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saofranciscoararuna2.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saofranciscoararuna2
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saofranciscoararuna2

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saojosecuite.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saojosecuite
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saojosecuite

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saojosemangabeira.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saojosemangabeira
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saojosemangabeira

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saojosemaranatha.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saojosemaranatha
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saojosemaranatha

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saomarcos.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saomarcos
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saomarcos

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saomiguelserraredonda.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saomiguelserraredonda
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saomiguelserraredonda

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saopedro.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saopedro
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saopedro

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saosebastiaojuarez.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saosebastiaojuarez
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saosebastiaojuarez

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saosebastiaoumbuzeiro.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saosebastiaoumbuzeiro
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saosebastiaoumbuzeiro

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Saovicente.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saovicente
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Saovicente

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\SF.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% SF
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% SF

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\SG.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% SG
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% SG

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\SGconv.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% SGconv
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% SGconv

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Shekinah.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Shekinah
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Shekinah

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sheknahgba.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sheknahgba
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sheknahgba

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sjramos.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sjramos
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sjramos

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sobradotransportadora.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sobradotransportadora
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sobradotransportadora

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sossego.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sossego
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sossego

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sousa.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sousa
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sousa

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Sumeautoposto.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sumeautoposto
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Sumeautoposto

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Suprema.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Suprema
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Suprema

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Thelux.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Thelux
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Thelux

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Timboazul.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Timboazul
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Timboazul

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Umbuzeirense.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Umbuzeirense
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Umbuzeirense

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Vip.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Vip
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Vip

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Vovozilda.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Vovozilda
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Vovozilda

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Vovozildamaragogi.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Vovozildamaragogi
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Vovozildamaragogi

@echo off

set x=%DATE:~0,2%-%DATE:~3,2%-%DATE:~6,4%
echo %x%
set date=%x%
echo %date%

   set BACKUP_FILE=C:\Backups_Novo\Zabele.backup
   echo backup file name is %BACKUP_FILE%
   SET PGPASSWORD=j0l0t1gT4nDpcaworrXlKQjuGcF7
   echo on
   bin\pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Zabele
pg_dump -h pgsql.e-prosys.com -p 5432 -U postgres -F c -b -v -f %BACKUP_FILE% Zabele

@echo off
echo Backup diario concluido (144 bancos).
