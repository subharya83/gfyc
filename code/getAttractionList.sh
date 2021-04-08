states=('AL' 'AK' 'AZ' 'AR' 'CA' 'CO' 'CT' 'DE' 'DC' 'FL' 'GA' 'HI' 'ID' 'IL' 
 'IN' 'IA' 'KS' 'KY' 'LA' 'ME' 'MD' 'MA' 'MI' 'MN' 'MS' 'MO' 'MT' 'NE' 'NV' 
 'NH' 'NJ' 'NM' 'NY' 'NC' 'ND' 'OH' 'OK' 'OR' 'PA' 'PR' 'RI' 'SC' 'SD' 'TN' 
 'TX' 'UT' 'VT' 'VI' 'VA' 'WA' 'WV' 'WI' 'WY')

urlbase='https://www.roadsideamerica.com/'

# Obtain list of attractions for states
for st in ${states[@]}; do
	urlstr=$urlbase"/location/"${st,,}"/all"
	ofile=../data/$st.txt
	det=../data/$st"_details.txt"
	echo "Retrieving contents from : $urlstr"
	if [ -ne $outfile]; then
    wget -q $urlstr
          cat all|grep "<li><span> <a href="|sed -e 's/^.*<strong>//g' -e 's/:<\/strong>//g' -e 's/<\/a>.*$//g' > $ofile
    echo "Saved contents into $ofile"
    rm all
  fi
	# Navigate to attraction URL to find address, descriptions etc.
	while IFS="" read -r p || [ -n "$p" ]
  do
    attr_suff=`echo "$p"|sed -e 's/.*<a href="//g' -e 's/">.*//g'`
    urlattr=$urlbase$attr_suff

    name=`curl -s --request POST $urlattr|grep -oP '(?<=<h1>).*(?=</h1)'`
    name=`echo $name|sed -e 's/\(.*\)<\/a>//g'`
    addr=`curl -s --request POST $urlattr|grep -oP '(?<=Address:).*(?=</a></dd><dt>)'|rev|cut -d'>' -f1|rev`
    echo \"$urlattr\"\|\"$name\"\|\"$addr\" | tee -a $det
  done < $ofile
  echo "Details file generated $det"
done