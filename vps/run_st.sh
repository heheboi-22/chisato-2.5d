cd /root/see-through
for s in 4 3; do
  .venv/bin/python inference/scripts/inference_psd.py --srcp /root/chisato25d/seed_000${s}_hires1280.png --save_dir /root/chisato25d/st_out --save_to_psd --tblr_split --group_offload > /root/chisato25d/st_$s.log 2>&1
  echo "done $s $?" >> /root/chisato25d/st_status.txt
done
