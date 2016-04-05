from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render

from ..forms import CertificateSearchForm
from .. import models
from ..services import ViciCertificateManager


class AbstractOverviewHandler:
    def __init__(self):
        self.request = None
        self.ENTRIES_PER_PAGE = 10

    @classmethod
    def by_request(cls, request):
        handler = cls()
        handler.request = request
        return handler

    def page_tag(self):
        raise NotImplementedError()

    def all_certificates(self):
        raise NotImplementedError()

    def _paginate(self, certificate_list, page=1):
        paginator = Paginator(certificate_list, self.ENTRIES_PER_PAGE)
        try:
            x509_list = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            x509_list = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            x509_list = paginator.page(paginator.num_pages)
        return x509_list

    def _search_for(self, all_certs, search_text):
        domains = models.Identity.objects.filter(subjectaltname__contains=search_text)
        cert_ids = []
        for domain in domains:
            cert_ids.append(domain.certificate.id)
        return all_certs.filter(id__in=cert_ids)

    def handle(self):
        search_pattern = ""
        page = 1
        if self.request.method == "GET":
            result = self.all_certificates()
        else:
            form = CertificateSearchForm(self.request.POST)
            if not form.is_valid():
                result = self.all_certificates()
            else:
                search_pattern = form.cleaned_data["search_text"]
                all_certs = self.all_certificates()
                result = self._search_for(all_certs, search_pattern)
                page = form.cleaned_data["page"]
        x509_list = self._paginate(result, page=page)
        return render(self.request, 'certificates/overview.html',
                      {'publics': x509_list, "view": self.page_tag(), "search_pattern": search_pattern})


class ViciOverviewHandler(AbstractOverviewHandler):
    def page_tag(self):
        return "vici"

    def all_certificates(self):
        ViciCertificateManager.reload_certs()
        return models.ViciCertificate.objects.all()


class EntityOverviewHandler(AbstractOverviewHandler):
    def page_tag(self):
        return "entities"

    def all_certificates(self):
        return models.UserCertificate.objects.filter(is_CA=False)


class MainOverviewHandler(AbstractOverviewHandler):
    def page_tag(self):
        return "all"

    def all_certificates(self):
        return models.UserCertificate.objects.all()


class RootOverviewHandler(AbstractOverviewHandler):
    def page_tag(self):
        return "root"

    def all_certificates(self):
        return models.UserCertificate.objects.filter(is_CA=True)