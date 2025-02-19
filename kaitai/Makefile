SRCS =$(wildcard *.ksy)
DOTS =$(SRCS:.ksy=.dot)
SVGS =$(SRCS:.ksy=.svg)
PY  =../src/spana/speak_and_spell_2019.py

ALL_OUTS += $(DOTS) $(SVGS) $(PY)

all: $(ALL_OUTS)

$(DOTS): %.dot : %.ksy
	ksc -t graphviz $<

$(SVGS): %.svg : %.dot
	 dot $< -Tsvg > $@

$(PY): $(SRCS)
	ksc -t python --outdir ../src/spana/ $<

clean:
	-rm -f $(ALL_OUTS)

.PHONY: all clean


