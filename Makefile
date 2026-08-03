TEXFILES = *.tex

all: paper.pdf

paper.pdf: $(TEXFILES)
	pdflatex paper.tex
	bibtex paper
	pdflatex paper.tex
	pdflatex paper.tex

clean:
	rm -f *.ilg *.aux *.log *.dvi *.idx *.toc *.lof *.lot
	rm -f *.blg *.bbl *~
	rm -f paper.out paper.pdf comment.cut

update:
	git pull