#!/usr/bin/env python
#coding = utf-8

# parse xml from pubmed
# in this python script, we want to generate two kinds of object:
#  - Article(Node)
#  - citation relationship(Edge)
# Since we can get a xml document in once query, and this xml document can contains 1 or more than 1 articles, the Node we will generate also more than 1.
# Besides, The citation information is contained in `xml -> artical -> reference` element, so we can extract them from xml as well. 
# We need to define a new class to descript the article object, which should contain Title, Abstract(if available), Author, Date, DOI, and the most important, the PMID.
# For Edge storage, we can use a `nx2` matrix and use PMID as main key
#   For example:
#       [[111,222],
#        [111,333]]
#   This means article "111" citated article "222" and "333"

# What about the articles citated our queried article? may be we should use other method to get it.

from datetime import datetime
from xml.dom.minidom import parseString
import json
import random
import requests
import http.server
import socketserver
import os,sys
import argparse

class ArticleObject:
    PMID       = 0
    title      = ""
    journal    = ""
    authorList = []
    DOI        = ""
    date       = ""
    PMC        = ""
    citation   = ""
    def __init__(self,PMID: int): 
        # when initialize an `ArticleObject` object, the PMID parameter is needed.
        # If the PMID is not avaliable, you can set PMID to a negative interger alternatively, 
        # then later when these information is available, you can use `ArticleObject.fromDict()`
        # or other methods to correct PMID and other information.
        self.PMID  = PMID
    def setTitle(self,title: str):
        self.title = title
    def setJournal(self,journal: str):
        self.journal    = journal
    def setAuthorList(self,authorList: list):
        self.authorList = authorList
    def setDOI(self, DOI: str):
        self.DOI   = DOI
    def setDate(self,date: str):
        self.date  = date
    def setPMC(self, PMC:str):
        self.PMC   = PMC
    def setCitation(self, citation:str):
        self.citation = citation
    def toDict(self) -> dict:
        dt = {
                "PMID":     self.PMID,
                "title":    self.title,
                "journal":  self.journal,
                "authorList":self.authorList,
                "DOI":      self.DOI,
                "date":     self.date,
                "PMC":      self.PMC,
                "citation": self.citation
            }
        return dt

    # Some times we need a more simple dict, which doesn't contain empty term.
    # So we provide this function:
    def toSimpleDict(self) -> dict:
        dt = {"PMID":self.PMID}
        if(self.title   != ""): dt["title"]     = self.title
        if(self.journal != ""): dt["journal"]   = self.journal
        if(self.DOI     != ""): dt["DOI"]       = self.DOI
        if(self.date    != ""): dt["date"]      = self.date
        if(self.PMC     != ""): dt["PMC"]       = self.PMC
        if(self.citation!= ""): dt["citation"]  = self.citation
        if(len(self.authorList)>=1): dt["authorList"]= self.authorList
        return dt

    def fromDict(self,dt):
        if("PMID"       in dt): self.PMID       = dt["PMID"]
        if("title"      in dt): self.title      = dt["title"]
        if("journal"    in dt): self.journal    = dt["journal"]
        if("authorList" in dt): self.authorList = dt["authorList"]
        if("DOI"        in dt): self.DOI        = dt["DOI"]
        if("date"       in dt): self.date       = dt["date"]
        if("PMC"        in dt): self.PMC        = dt["PMC"]
        if("citation"   in dt): self.citation   = dt["citation"]
    # some times for one artile we generate two objects, then we need to merge then into one.
    def merge(self, artObj1): 
        # PMID check:
        if(self.PMID<0 and artObj1.PMID>0):
            self.PMID = artObj1.PMID
        # title check:
        if(len(self.title) < len(artObj1.title)):
            self.title = artObj1.title
        # journal check:
        if(len(self.journal) < len(artObj1.journal)):
            self.journal = artObj1.journal
        # authorList check:
        if(len(self.authorList) < len(artObj1.authorList)):
            for auth in artObj1.authorList:
                if(auth not in self.authorList):
                    (self.authorList).append(auth)
        # DOI check:
        if(len(self.DOI) < len(artObj1.DOI)):
            self.DOI = artObj1.DOI
        # Date check:
        if(len(self.date) < len(artObj1.date)):
            self.date = artObj1.date
        # PMC check:
        if(len(self.PMC) < len(artObj1.PMC)):
            self.PMC = artObj1.PMC
        # citation check:
        if(len(self.citation) < len(artObj1.citation)):
            self.citation = artObj1.citation

# Extract reference list
def processPubmedData(element) -> (list,list): 
    PMID = -1
    articleIdList = element.getElementsByTagName("ArticleIdList")[0].getElementsByTagName("ArticleId")
    for i in articleIdList:
        if(i.getAttribute("IdType")=="pubmed"):
            PMID = int(i.childNodes[0].nodeValue)
            break
    #print(element.childNodes)# debug
    citMat = [] # citation matrix, is used to storage edge information of citation map
    citArt = [] # citation articles, is used to storage reference article information
    try:
        refListNodes = element.getElementsByTagName("ReferenceList")[0].getElementsByTagName("Reference")
        for ref in refListNodes:
            cit = ref.getElementsByTagName("Citation")[0]
            citation = cit.childNodes[0].nodeValue # citation text
            art_info_dt = {"pubmed":-2,"doi":"","pmc":""}
            try: # some times the referenced article don't have PMID, so we need confirm here:
                art = ref.getElementsByTagName("ArticleIdList")[0]
                artIdList = art.getElementsByTagName("ArticleId")
                for obj in artIdList:
                    idType = obj.getAttribute("IdType")
                    text   = obj.childNodes[0].nodeValue
                    if(idType=="pubmed"): text = int(text)
                    art_info_dt[idType] = text
            except: # and if PMID doesn't exist, we generate a negative random number to represent it.
                pass
            if(art_info_dt["pubmed"]<0):
                art_info_dt["pubmed"] = random.randint(-999999,-100000)
            artObj = ArticleObject(art_info_dt["pubmed"])
            artObj.setCitation(citation)
            artObj.setDOI(art_info_dt["doi"])
            artObj.setPMC(art_info_dt["pmc"])
            citArt.append(artObj)
            citMat.append([PMID,art_info_dt["pubmed"]])
    except:
        pass
    return (citMat,citArt)

# Extract article information
def processMedlineCitation(element) -> ArticleObject: 
    # PMID
    PMID = int(element.getElementsByTagName("PMID")[0].childNodes[0].nodeValue)
    # Date
    #print(element.childNodes) #debug
    try:
        DateNode = element.getElementsByTagName("DateCompleted")[0]
        Year  = DateNode.getElementsByTagName("Year" )[0].childNodes[0].nodeValue
        Month = DateNode.getElementsByTagName("Month")[0].childNodes[0].nodeValue
        Day   = DateNode.getElementsByTagName("Day"  )[0].childNodes[0].nodeValue
    except:
        try:
            DateNode = element.getElementsByTagName("DateRevised")[0]
            Year  = DateNode.getElementsByTagName("Year" )[0].childNodes[0].nodeValue
            Month = DateNode.getElementsByTagName("Month")[0].childNodes[0].nodeValue
            Day   = DateNode.getElementsByTagName("Day"  )[0].childNodes[0].nodeValue
        except:
            Year =  "0000"
            Month = "00"
            Day = "00"
    #Date  = datetime.date(datetime.strptime(f"{Year}-{Month}-{Day}","%Y-%M-%d")) # format date string into date object
    finally:
        Date  = f"{Year}-{Month}-{Day}"
    # Article metadata
    artMeta = element.getElementsByTagName("Article")[0]
    ## Journal
    journal = artMeta.getElementsByTagName("Journal")[0].getElementsByTagName("Title")[0].childNodes[0].nodeValue
    ## Title
    title   = artMeta.getElementsByTagName("ArticleTitle")[0].childNodes[0].nodeValue
    ## DOI
    doi = ""
    for e in  artMeta.getElementsByTagName("ELocationID"):
        if(e.getAttribute("EIdType")=="doi"):
            doi = e.childNodes[0].nodeValue
    ## AuthorList
    authList = []
    authNode = artMeta.getElementsByTagName("AuthorList")[0].getElementsByTagName("Author")
    for a in authNode:
        try:
            lastName = a.getElementsByTagName("LastName")[0].childNodes[0].nodeValue
            foreName = a.getElementsByTagName("ForeName")[0].childNodes[0].nodeValue
            authList.append(f"{lastName} {foreName}")
        except:
            try:
                collectName = a.getElementsByTagName("CollectiveName")[0].childNodes[0].nodeValue
                authList.append(collectName)
            except:
                pass
    # Then we can generate an `ArticleObject` object
    artObj = ArticleObject(PMID)
    artObj.setTitle(title)
    artObj.setJournal(journal)
    artObj.setAuthorList(authList)
    artObj.setDOI(doi)
    artObj.setDate(Date)
    return artObj

def processPubmedArticle(element) -> (ArticleObject,list): # Top level process
    artObj = processMedlineCitation(element.getElementsByTagName("MedlineCitation")[0])
    (citEdg,citArt) = processPubmedData(element.getElementsByTagName("PubmedData")[0])
    return (artObj,citEdg,citArt)

# Parse citation information from a xml string
def parseCitation(string):
    data = parseString(string).documentElement
    linkSets = data.getElementsByTagName("LinkSet")[0].getElementsByTagName("LinkSetDb")
    dt = {}
    for s in linkSets:
        DbTo     = s.getElementsByTagName("DbTo"    )[0].childNodes[0].nodeValue
        LinkName = s.getElementsByTagName("LinkName")[0].childNodes[0].nodeValue
        Links    = s.getElementsByTagName("Link")
        linkList = []
        for l in Links:
            linkList.append(int(l.getElementsByTagName("Id")[0].childNodes[0].nodeValue))
        dt[LinkName] = {"DbTo":DbTo,"linkList":linkList}
        print(f"LinkName={LinkName}")
        print(f"Length of this category:{len(linkList)}")
    if("pubmed_pubmed_citedin" in dt):
        return dt["pubmed_pubmed_citedin"]["linkList"]
    else: return []

# Get citation information
def getCitations(pmid:int) -> (list,list):
    print(f"get citation information of article `{pmid}`")
    # get full citation list from elink API
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?db=pubmed&api_key=ae4e7d262dc452dece0be6c4a7e06d9ccc09&id={pmid}"
    req = requests.get(url)
    req.encoding = "utf-8"
    txt = req.text
    citations = parseCitation(txt)
    citEdge = []
    for c in citations:
        citEdge.append([c,pmid])
    #print(f"In subprecess`getCitations()`, citEdge=")
    #print(citEdge)
    # get details of each citation article from efetch API
    citDetails = []
    if(len(citations)>0):
        queryID = ""
        for c in citations: queryID += f"{c},"
        queryID = queryID[0:-1]
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&api_key=ae4e7d262dc452dece0be6c4a7e06d9ccc09&id={queryID}"
        print(url)
        req = requests.get(url)
        req.encoding = "utf-8"
        txt = req.text
        data = parseString(txt).documentElement
        PubmedArticleSet = data.getElementsByTagName("PubmedArticle") # PubMed Article Object
        for e in PubmedArticleSet:
            artObj,c1,c2 = processPubmedArticle(e)
            citDetails.append(artObj)
    return (citEdge,citDetails)


# The top-level process function.
# Input a xml string, parse xml, (query addtional information if necessary),
# and return a dict which can be exported as json and visualized in echarts.
def parseXML(xmlText): 
    # define a dict data structure, for data storage
    # this dict will be used to generate echart network plot
    data_dt = {
            "type": "force",
            "categories": [
                {"name":"reference","keyword":{},"base":"reference"}, # all articles referenced by query articles
                {"name":"query",    "keyword":{},"base":"query"    }, # all article queries
                {"name":"citation", "keyword":{},"base":"citation" }, # all articles which cite these query articles
                ],
            "nodes":[],
            "links":[]
            }
    # Read XML document
    data = parseString(xmlText).documentElement
    PubmedArticleSet = data.getElementsByTagName("PubmedArticle") # PubMed Article Object
    # use a dict to avoid duplicated object
    PMID_dict = {} # dict of "int" type. key: PMID; value: article index in `data_dt["nodes"]`
    i = 0
    # also, to make sure all "query" articles can have correct category, 
    # these reference articles should append later
    refArticles = [] # list of "ArticleObject" type
    # these citation articles should append later
    citArticles = [] # list of "ArticleObject" type
    # we also need a container to storage edge information
    edgeList = []
    # process all query result
    for e in PubmedArticleSet:
        artObj,refEdge,refArt = processPubmedArticle(e)
        artObj_dt = artObj.toDict()
        artObj_dt["category"] = 1 # set category as "query"
        pmid = artObj_dt["PMID"]
        artObj_dt["name"] = json.dumps(artObj.toSimpleDict(),indent="\t")
        data_dt["nodes"].append(artObj_dt);PMID_dict[pmid] = i;i+=1
        # storage reference information
        #print("refEdge=")
        #print(refEdge)
        edgeList    += refEdge
        refArticles += refArt
        # get citations and storage citation information
        citEdge,citArt = getCitations(pmid)
        #print("citEdge=")
        #print(citEdge)
        edgeList    += citEdge
        citArticles += citArt
    for c in citArticles:
        c_dt = c.toDict()
        c_dt["category"] = 2 # set category as "citation"
        pmid = c_dt["PMID"] 
        #print(f"cit\t{pmid}")
        c_dt["name"] = json.dumps(c.toSimpleDict(),indent="\t")
        if(pmid not in PMID_dict):
            data_dt["nodes"].append(c_dt);PMID_dict[pmid] = i;i+=1
    for f in refArticles:
        f_dt = f.toDict()
        f_dt["category"] = 0 # set category as "reference"
        pmid = f_dt["PMID"]
        #print(f"ref\t{pmid}")
        f_dt["name"] = json.dumps(f.toSimpleDict(),indent="\t")
        if(pmid not in PMID_dict):
            data_dt["nodes"].append(f_dt);PMID_dict[pmid] = i;i+=1
    for d in edgeList:
        #print(d)
        source_pmid = d[0]
        target_pmid = d[1]
        source_index = PMID_dict[source_pmid]
        target_index = PMID_dict[target_pmid]
        edge_dt = {"source":source_index,"target":target_index}
        if(edge_dt not in data_dt["links"]):
            data_dt["links"].append(edge_dt)
    return data_dt

def queryPubmed(pmidList):
    #print(pmidList)
    queryId = ""
    for i in pmidList:
        queryId += f"{i},"
    queryId = queryId[0:-1]
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&api_key=ae4e7d262dc452dece0be6c4a7e06d9ccc09&id={queryId}"
    print(url)
    req = requests.get(url)
    req.encoding = "utf-8"
    txt = req.text
    return txt


def getPmidListFromFile(fpath):
    pmidList = []
    with open(fpath,'r') as f:
        for line in f:
            if(line[0]=="#"):continue
            if(len(line)<2):continue
            if("#" in line):line = line.split("#")[0]
            a = line.strip().split()
            b = a[0]
            for c in [",",".",":",";","#","*","&","%","`"]:
                b = b.replace(c,"")
            try: pmidList.append(int(b))
            except: pass
    return pmidList

def getPmidListFromString(string):
    pmidList = []
    for c in string.strip().split(","):
        try: pmidList.append(int(c))
        except: pass
    return pmidList



if(__name__=="__main__"):
    prs = argparse.ArgumentParser()
    grp = prs.add_mutually_exclusive_group()
    grp.add_argument("-f","--file",action="store",type=str,help="PMID list file.")
    grp.add_argument("-l","--list",action="store",type=str,help="PMID list(comma seperate).")
    prs.add_argument("-m","--max", action="store",type=int,help="Max limitation of query article number. Default is 10.",default=10)
    prs.add_argument("-p","--port",action="store",type=int,help="Network port of the report server. Default is using random number.",default=-999)
    args = prs.parse_args()

    pmidList = []
    if(args.file!=None):
        pmidList = getPmidListFromFile(args.file)
    if(args.list!=None):
        pmidList = getPmidListFromString(args.list)
    if(len(pmidList)==0):
        prs.print_help()
        sys.exit(0)
    
    print("Max limitation of query article number is {}.".format(args.max if args.max>1 else 10))
    if(args.max>1 and len(pmidList)>args.max):
        pmidList = pmidList[0:args.max]

    txt = queryPubmed(pmidList)
    data_dt = parseXML(txt)
    data_json = json.dumps(data_dt,indent="\t")
    f = open("citation_map.json","w")
    f.write(data_json)
    f.close()
    
    if(args.port<0):
        print("Default port number will be set.")
        PORT = random.randint(10000,65535)
    elif(args.port>65536):
        print("Illegal port number. The report server will use default port instead.")
        PORT = random.randint(10000,65535)
    else:
        PORT = args.port
        print(f"User specify the server port as {PORT}.")

    Handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"The report is serving at port {PORT}.")
        print(f"Please open the following URL to check report: \033[36m http://localhost:{PORT} \033[0m")
        print("To stop web server, Press `Ctrl+C` ")
        # if host OS is windows or macOS, then open URL automatically.
        if(sys.platform=="win32" or sys.platform=="darwin"): 
            import webbrowser
            webbrowser.open(f"http://localhost:{PORT}",new=1)
        # Start web server
        httpd.serve_forever()







