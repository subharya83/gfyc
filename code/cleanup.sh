states=('AL' 'AK' 'AZ' 'AR' 'CA' 'CO' 'CT' 'DE' 'DC' 'FL' 'GA' 'HI' 'ID' 'IL'
 'IN' 'IA' 'KS' 'KY' 'LA' 'ME' 'MD' 'MA' 'MI' 'MN' 'MS' 'MO' 'MT' 'NE' 'NV'
 'NH' 'NJ' 'NM' 'NY' 'NC' 'ND' 'OH' 'OK' 'OR' 'PA' 'PR' 'RI' 'SC' 'SD' 'TN'
 'TX' 'UT' 'VT' 'VI' 'VA' 'WA' 'WV' 'WI' 'WY')

for st in ${states[@]}; do
	det=../data/$st"_details.txt"
	tmpfile=../data/tmp
	# Navigate to attraction URL to find address, descriptions etc.
	while IFS="" read -r p || [ -n "$p" ]
  do
    name_url=`echo $p|sed 's/::/\|/g'|cut -d'|' -f1|sed -e 's/\"//g'|awk '{$1=$1};1'`
    name_attr=`echo $p|sed 's/::/\|/g'|cut -d'|' -f2|sed -e 's/^\(.*\)a>://g' -e 's/\"//g'|awk '{$1=$1};1'`
    name_addr=`echo $p|sed 's/::/\|/g'|cut -d'|' -f3|sed -e 's/\"//g'|awk '{$1=$1};1'`
    echo \"$name_url\"\|\"$name_attr\"\|\"$name_addr\" | tee -a $tmpfile
  done < $det
  mv $tmpfile $det
  echo "Details file generated $det"
done