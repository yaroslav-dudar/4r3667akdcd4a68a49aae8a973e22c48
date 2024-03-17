ARRAY=('a' 'b' 'c' 'd' 'e' 'f' 'g' 'h' 'i' 'j' 'k' 'l' 'm' 'n' 'o' 'p' 'q' 'r' 's' 't' 'u' 'v' 'w' 'x' 'y' 'z')
VALUES="INSERT INTO test.events (random_character, random_digit) VALUES "
for ((i=1; i<=20; i=i+1))
do 
      DIGIT=$(( ( RANDOM % 9 )  + 1 ))
      CHAR=${ARRAY[$RANDOM % ${#ARRAY[@]}]}
      VALUES+="(\"$CHAR\", $DIGIT),"
done


INSERT_SQL="bq query --use_legacy_sql=false '${VALUES::-1}'"
echo $INSERT_SQL
eval $INSERT_SQL
