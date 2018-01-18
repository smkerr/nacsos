python3 manage.py graph_models scoping | dot -Tpdf > models.pdf
python3 manage.py graph_models tmv_app | dot -Tpdf > models_tmv.pdf
python3 manage.py graph_models parliament | dot -Tpdf > models_parliament.pdf
python3 manage.py graph_models parliament | dot -Tpng > models_parliament.png
python3 manage.py graph_models scoping tmv_app  | dot -Tpdf > all_models.pdf
